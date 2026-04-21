#include <stdio.h>
#include "../shell.h"

int shell_help(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    puts("Builtins:");
    puts("  cd [dir]      Change the current directory");
    puts("  pwd           Print the current directory");
    puts("  help          Show this help");
    puts("  exit          Exit the shell");
    puts("  delphi [on|off] Toggle Delphi mode");
    puts("  dump          Dump the local symbol table");
    return 0;
}
