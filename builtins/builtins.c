#include "../shell.h"

//note: when adding new builtins, i stll need to tell executor 
// ex. user types dump, we support dump but if executor doesnt know then i sit wondering why it doesnt work for an hour or executes external dump

struct builtin_s builtins[] =
{   
    { "dump"    , dump       },
};

int builtins_count = sizeof(builtins)/sizeof(struct builtin_s);