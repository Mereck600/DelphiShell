#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <limits.h>
#include <unistd.h>
#include "../shell.h"

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

int shell_pwd(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    char cwd[PATH_MAX];
    if(!getcwd(cwd, sizeof(cwd)))
    {
        perror("pwd");
        return 1;
    }

    printf("%s\n", cwd);
    return 0;
}
