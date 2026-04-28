#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include "shell.h"
#include "delphi_bridge.h"

#ifndef _WIN32
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#endif

#ifdef _WIN32
#define DELPHI_PYTHON ".venv\\Scripts\\python.exe"
#else
#define DELPHI_PYTHON ".venv/bin/python"
#endif

#ifndef _WIN32
#define DELPHI_SOCKET_PATH "/tmp/delphi_shell.sock"
#endif

static void trim_newline(char *s)
{
    // Removes trailing newline characters from subprocess output in place.
    if (!s) return;
    size_t n = strlen(s);
    while (n > 0 && (s[n-1] == '\n' || s[n-1] == '\r')) {
        s[n-1] = '\0';
        n--;
    }
}

static int extract_json_value(const char *json, const char *key, char *out, size_t out_size)
{
    // Pulls a JSON string value out of the flat response and preserves escaped quotes.
    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\":\"", key);

    char *start = strstr((char *)json, pattern);
    if (!start) return 0;
    start += strlen(pattern);

    size_t j = 0;
    int escaped = 0;

    for (size_t i = 0; start[i] != '\0'; i++) {
        char ch = start[i];

        if (escaped) {
            if (j + 1 >= out_size) return 0;

            switch (ch) {
                case 'n':
                    out[j++] = '\n';
                    break;
                case 'r':
                    out[j++] = '\r';
                    break;
                case 't':
                    out[j++] = '\t';
                    break;
                case '\\':
                case '"':
                case '/':
                    out[j++] = ch;
                    break;
                default:
                    out[j++] = ch;
                    break;
            }

            escaped = 0;
            continue;
        }

        if (ch == '\\') {
            escaped = 1;
            continue;
        }

        if (ch == '"') {
            out[j] = '\0';
            return 1;
        }

        if (j + 1 >= out_size) return 0;
        out[j++] = ch;
    }

    if (j < out_size) {
        out[j] = '\0';
    }

    if (escaped) return 0;
    return 1;
}

static int extract_json_array(const char *json, const char *key, char *out, size_t out_size)
{
    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\":[", key);

    const char *start = strstr(json, pattern);
    if (!start) return 0;
    start += strlen(pattern) - 1;

    size_t j = 0;
    int depth = 0;
    int in_string = 0;
    int escaped = 0;

    for (size_t i = 0; start[i] != '\0'; i++) {
        char ch = start[i];

        if (j + 1 >= out_size) return 0;
        out[j++] = ch;

        if (escaped) {
            escaped = 0;
            continue;
        }

        if (ch == '\\' && in_string) {
            escaped = 1;
            continue;
        }

        if (ch == '"') {
            in_string = !in_string;
            continue;
        }

        if (in_string) {
            continue;
        }

        if (ch == '[') {
            depth++;
        } else if (ch == ']') {
            depth--;
            if (depth == 0) {
                out[j] = '\0';
                return 1;
            }
        }
    }

    return 0;
}

static int execute_action_json(const char *json);

#ifndef _WIN32
static int write_all(int fd, const char *buf, size_t len)
{
    size_t written = 0;

    while (written < len) {
        ssize_t n = write(fd, buf + written, len - written);
        if (n <= 0) {
            return 0;
        }
        written += (size_t)n;
    }

    return 1;
}

static int read_line_from_fd(int fd, char *out, size_t out_size)
{
    size_t used = 0;

    while (used + 1 < out_size) {
        char ch;
        ssize_t n = read(fd, &ch, 1);
        if (n <= 0) {
            break;
        }
        if (ch == '\n') {
            break;
        }
        out[used++] = ch;
    }

    out[used] = '\0';
    return used > 0;
}

static void json_escape_string(const char *src, char *dst, size_t dst_size)
{
    size_t j = 0;

    for (size_t i = 0; src[i] != '\0' && j + 2 < dst_size; i++) {
        char ch = src[i];
        if (ch == '"' || ch == '\\') {
            dst[j++] = '\\';
            dst[j++] = ch;
        } else if (ch == '\n') {
            dst[j++] = '\\';
            dst[j++] = 'n';
        } else if (ch == '\r') {
            dst[j++] = '\\';
            dst[j++] = 'r';
        } else if (ch == '\t') {
            dst[j++] = '\\';
            dst[j++] = 't';
        } else {
            dst[j++] = ch;
        }
    }

    dst[j] = '\0';
}

static int connect_delphi_server(void)
{
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, DELPHI_SOCKET_PATH, sizeof(addr.sun_path) - 1);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
        close(fd);
        return -1;
    }

    return fd;
}

static void start_delphi_server(void)
{
    char cmd[1024];
    snprintf(
        cmd,
        sizeof(cmd),
        "nohup %s delphi/delphi_server.py --socket %s >/tmp/delphi_server.log 2>&1 &",
        DELPHI_PYTHON,
        DELPHI_SOCKET_PATH
    );
    system(cmd);
}

static int request_delphi_server(const char *input, char *response, size_t response_size)
{
    char request_text[4096];
    char request_json[4608];

    json_escape_string(input, request_text, sizeof(request_text));
    snprintf(request_json, sizeof(request_json), "{\"text\":\"%s\"}\n", request_text);

    int fd = connect_delphi_server();
    if (fd < 0) {
        start_delphi_server();

        for (int i = 0; i < 20; i++) {
            usleep(100000);
            fd = connect_delphi_server();
            if (fd >= 0) {
                break;
            }
        }
    }

    if (fd < 0) {
        return 0;
    }

    int ok = write_all(fd, request_json, strlen(request_json)) &&
             read_line_from_fd(fd, response, response_size);
    close(fd);
    return ok;
}
#endif

static int execute_plan_steps(const char *steps_json)
{
    const char *cursor = steps_json;

    while (*cursor != '\0') {
        while (*cursor != '\0' && *cursor != '{') {
            cursor++;
        }

        if (*cursor == '\0') {
            break;
        }

        char step_json[4096] = {0};
        size_t j = 0;
        int depth = 0;
        int in_string = 0;
        int escaped = 0;

        while (*cursor != '\0') {
            char ch = *cursor++;

            if (j + 1 >= sizeof(step_json)) {
                fprintf(stderr, "Delphi: plan step too large\n");
                return 1;
            }

            step_json[j++] = ch;

            if (escaped) {
                escaped = 0;
                continue;
            }

            if (ch == '\\' && in_string) {
                escaped = 1;
                continue;
            }

            if (ch == '"') {
                in_string = !in_string;
                continue;
            }

            if (in_string) {
                continue;
            }

            if (ch == '{') {
                depth++;
            } else if (ch == '}') {
                depth--;
                if (depth == 0) {
                    step_json[j] = '\0';
                    if (execute_action_json(step_json) != 0) {
                        return 1;
                    }
                    break;
                }
            }
        }
    }

    return 0;
}

static int execute_action_json(const char *json)
{
    char mode[64] = {0};

    if (!extract_json_value(json, "mode", mode, sizeof(mode))) {
        fprintf(stderr, "Delphi: failed to parse mode from response: %s\n", json);
        return 1;   
    }

    if (strcmp(mode, "answer") == 0) {
        char text[4096] = {0};

        if (!extract_json_value(json, "text", text, sizeof(text))) {
            fprintf(stderr, "Delphi: missing text in answer response\n");
            return 1;
        }

        printf("%s\n", text);
        return 0;
    }

    if (strcmp(mode, "cd") == 0) {
        char path[1024] = {0};
        char *argv[3];

        if (!extract_json_value(json, "path", path, sizeof(path))) {
            fprintf(stderr, "Delphi: missing path for cd action\n");
            return 1;
        }

        argv[0] = "cd";
        argv[1] = path;
        argv[2] = NULL;
        fprintf(stderr, "[Delphi cd] %s\n", path);
        return shell_cd(2, argv);
    }

    if (strcmp(mode, "shell") == 0) {
        char shell_cmd[4096] = {0};

        if (!extract_json_value(json, "command", shell_cmd, sizeof(shell_cmd))) {
            fprintf(stderr, "Delphi: missing command for shell action\n");
            return 1;
        }

        fprintf(stderr, "[Delphi exec] %s\n", shell_cmd);
        return system(shell_cmd);
    }

    if (strcmp(mode, "run_file") == 0) {
        char run_cmd[4096] = {0};

        if (!extract_json_value(json, "command", run_cmd, sizeof(run_cmd))) {
            fprintf(stderr, "Delphi: missing command for run_file action\n");
            return 1;
        }

        fprintf(stderr, "[Delphi run] %s\n", run_cmd);
        return system(run_cmd);
    }

    if (strcmp(mode, "write_file") == 0) {
        char path[1024] = {0};
        char content[4096] = {0};

        if (!extract_json_value(json, "path", path, sizeof(path))) {
            fprintf(stderr, "Delphi: missing path\n");
            return 1;
        }

        if (!extract_json_value(json, "content", content, sizeof(content))) {
            fprintf(stderr, "Delphi: missing content\n");
            return 1;
        }

        FILE *out = fopen(path, "w");
        if (!out) {
            fprintf(stderr, "Delphi: failed to write file: %s\n", path);
            return 1;
        }

        fprintf(out, "%s", content);
        fclose(out);

        printf("[Delphi wrote %s]\n", path);
        return 0;
    }

    if (strcmp(mode, "plan") == 0) {
        char steps[8192] = {0};

        if (!extract_json_array(json, "steps", steps, sizeof(steps))) {
            fprintf(stderr, "Delphi: missing steps for plan action\n");
            return 1;
        }

        fprintf(stderr, "[Delphi plan] %s\n", steps);
        return execute_plan_steps(steps);
    }

    fprintf(stderr, "Delphi: unsupported mode: %s\n", mode);
    return 1;
}

int run_delphi_input(const char *input)
{
    if (!input) return 1;

    char response[8192] = {0};

#ifndef _WIN32
    if (!request_delphi_server(input, response, sizeof(response))) {
#endif
        char escaped[2048];
        size_t j = 0;

        for (size_t i = 0; input[i] != '\0' && j < sizeof(escaped) - 2; i++) {
            if (input[i] == '"' || input[i] == '\\') {
                escaped[j++] = '\\';
            }
            escaped[j++] = input[i];
        }
        escaped[j] = '\0';

        char cmd[4096];
        snprintf(cmd, sizeof(cmd), DELPHI_PYTHON " delphi/infer_delphi.py \"%s\"", escaped);

        fprintf(stderr, "[Delphi cmd] %s\n", cmd);

        FILE *fp = popen(cmd, "r");
        if (!fp) {
            fprintf(stderr, "error: failed to launch Delphi model\n");
            return 1;
        }

        size_t total = fread(response, 1, sizeof(response) - 1, fp);
        response[total] = '\0';

        int status = pclose(fp);
        (void)status;
#ifndef _WIN32
    } else {
        fprintf(stderr, "[Delphi cmd] %s %s\n", DELPHI_PYTHON, "delphi/delphi_server.py");
    }
#endif

    trim_newline(response);

    fprintf(stderr, "[Delphi raw] %s\n", response);

    if (response[0] == '\0') {
        fprintf(stderr, "Delphi: empty response from model\n");
        return 1;
    }

    if (!strstr(response, "\"mode\"")) {
        fprintf(stderr, "Delphi: invalid response: %s\n", response);
        return 1;
    }

    return execute_action_json(response);
}
