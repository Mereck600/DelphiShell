#include "../shell.h"
#include "../symtab/symtab.h"

// Simple, This function implements the dump
// builtin utility, which prints the contents of the local symbol table.

//note: when adding new builtins, i stll need to tell executor 
// ex. user types dump, we support dump but if executor doesnt know then i sit wondering why it doesnt work for an hour or executes external dump

int dump(int argc, char **argv)
{
    dump_local_symtab();
    return 0;
}