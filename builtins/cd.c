#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <unistd.h>
#include "../shell.h"
#include "../symtab/symtab.h"

static void update_pwd(const char *path)
{
    struct symtab_entry_s *entry = get_symtab_entry("PWD");
    if(!entry)
    {
        entry = add_to_symtab("PWD");
    }

    if(entry)
    {
        symtab_entry_setval(entry, (char *)path);
        entry->flags |= FLAG_EXPORT;
    }

    #ifdef _WIN32
    _putenv_s("PWD", path);
    #else
    setenv("PWD", path, 1);
    #endif
}

int shell_cd(int argc, char **argv)
{
    const char *target = NULL;

    if(argc > 2)
    {
        fprintf(stderr, "cd: too many arguments\n");
        return 1;
    }

    if(argc == 1)
    {
        target = getenv("HOME");
        if(!target || !*target)
        {
            target = getenv("USERPROFILE");
        }
    }
    else
    {
        target = argv[1];
    }

    if(!target || !*target)
    {
        fprintf(stderr, "cd: HOME is not set\n");
        return 1;
    }

    if(chdir(target) != 0)
    {
        perror("cd");
        return 1;
    }

    char cwd[PATH_MAX];
    if(getcwd(cwd, sizeof(cwd)))
    {
        update_pwd(cwd);
    }

    return 0;
}
