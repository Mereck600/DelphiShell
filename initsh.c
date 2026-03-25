#include <string.h>
#include "shell.h"
#include "symtab/symtab.h"

extern char **environ;

// This function initializes the symbol table stack (including the global symbol table) and scans the environment list, 
// adding each environment variable (and its value) to the table. 
// Lastly, the function adds two variables that we'll use to store our prompt strings, PS1 and PS2
void initsh(void)
{
    init_symtab();

    struct symtab_entry_s *entry;
    char **p2 = environ;

    while(*p2)
    {
        char *eq = strchr(*p2, '=');
        if(eq)
        {
            int len = eq-(*p2);
            char name[len+1];

            strncpy(name, *p2, len);
            name[len] = '\0';
            entry = add_to_symtab(name);

            if(entry)
            {
                symtab_entry_setval(entry, eq+1);
                entry->flags |= FLAG_EXPORT;
            }
        }
        else
        {
            entry = add_to_symtab(*p2);
        }
        p2++;
    }

    entry = add_to_symtab("PS1");
    symtab_entry_setval(entry, "$ ");

    entry = add_to_symtab("PS2");
    symtab_entry_setval(entry, "> ");
}