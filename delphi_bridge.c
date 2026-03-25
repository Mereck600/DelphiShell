#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "delphi_bridge.h"


#ifdef _WIN32
#define DELPHI_PYTHON ".venv\\Scripts\\python.exe"
#else
#define DELPHI_PYTHON ".venv/bin/python"
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
    // Pulls a simple string value out of the flat JSON response returned by Delphi.
    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\":\"", key);

    char *start = strstr((char *)json, pattern);
    if (!start) return 0;
    start += strlen(pattern);

    char *end = strchr(start, '"');
    if (!end) return 0;

    size_t len = (size_t)(end - start);
    if (len >= out_size) len = out_size - 1;

    strncpy(out, start, len);
    out[len] = '\0';
    return 1;
}

int run_delphi_input(const char *input)
{
    if (!input) return 1;

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
    snprintf(cmd, sizeof(cmd),
             DELPHI_PYTHON " delphi/infer_delphi.py \"%s\"",
             escaped);

    fprintf(stderr, "[Delphi cmd] %s\n", cmd);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "error: failed to launch Delphi model\n");
        return 1;
    }

    char response[8192] = {0};
    size_t total = fread(response, 1, sizeof(response) - 1, fp);
    response[total] = '\0';

    int status = pclose(fp);
    (void)status;

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

    char mode[64] = {0};

    if (!extract_json_value(response, "mode", mode, sizeof(mode))) {
        fprintf(stderr, "Delphi: failed to parse mode from response: %s\n", response);
        return 1;
    }

    if (strcmp(mode, "answer") == 0) {
        char text[4096] = {0};

        if (!extract_json_value(response, "text", text, sizeof(text))) {
            fprintf(stderr, "Delphi: missing text in answer response\n");
            return 1;
        }

        printf("%s\n", text);
        return 0;
    }

    if (strcmp(mode, "shell") == 0) {
        char shell_cmd[4096] = {0};

        if (!extract_json_value(response, "command", shell_cmd, sizeof(shell_cmd))) {
            fprintf(stderr, "Delphi: missing command for shell action\n");
            return 1;
        }

        fprintf(stderr, "[Delphi exec] %s\n", shell_cmd);
        return system(shell_cmd);
    }

    if (strcmp(mode, "run_file") == 0) {
        char run_cmd[4096] = {0};

        if (!extract_json_value(response, "command", run_cmd, sizeof(run_cmd))) {
            fprintf(stderr, "Delphi: missing command for run_file action\n");
            return 1;
        }

        fprintf(stderr, "[Delphi run] %s\n", run_cmd);
        return system(run_cmd);
    }

    if (strcmp(mode, "write_file") == 0) {
        char path[1024] = {0};
        char content[4096] = {0};

        if (!extract_json_value(response, "path", path, sizeof(path))) {
            fprintf(stderr, "Delphi: missing path\n");
            return 1;
        }

        if (!extract_json_value(response, "content", content, sizeof(content))) {
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

    fprintf(stderr, "Delphi: unsupported mode: %s\n", mode);
    return 1;
}