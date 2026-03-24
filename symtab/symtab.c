#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "../shell.h"
#include "../node.h"
#include "../parser.h"
#include "symtab.h"


struct symtab_stack_s symtab_stack; //this is the pointer to the st stack
int    symtab_level; // this is out current level in the stack

//unction initializes our symbol table stack, then allocates memory for, and initializes, our global symbol table.
void init_symtab(void)
{
    symtab_stack.symtab_count = 1;
    symtab_level = 0;

    struct symtab_s *global_symtab = malloc(sizeof(struct symtab_s));

    if(!global_symtab)
    {
        fprintf(stderr, "fatal error: no memory for global symbol table\n");
        exit(EXIT_FAILURE);
    }

    memset(global_symtab, 0, sizeof(struct symtab_s));
    symtab_stack.global_symtab  = global_symtab;
    symtab_stack.local_symtab   = global_symtab;
    symtab_stack.symtab_list[0] = global_symtab;
    global_symtab->level        = 0;
}

/* We call this function whenever 
* we want to create a new symbol table 
* (for example, when we're about to execute a shell function).
*/
struct symtab_s *new_symtab(int level)
{
    struct symtab_s *symtab = malloc(sizeof(struct symtab_s));

    if(!symtab)
    {
        fprintf(stderr, "fatal error: no memory for new symbol table\n");
        exit(EXIT_FAILURE);
    }

    memset(symtab, 0, sizeof(struct symtab_s));
    symtab->level = level;
    return symtab;
}


/*We use this function when we are done with the symbol table and 
* all of its entrues.   
*/
void free_symtab(struct symtab_s *symtab)
{
    if(symtab == NULL)
    {
        return;
    }

    for (int i = 0; i < HASH_SIZE; i++)
    {
        struct symtab_entry_s *entry = symtab->buckets[i];

        while(entry)
        {
            if(entry->name)
            {
                free(entry->name);
            }

            if(entry->val)
            {
                free(entry->val);
            }

            if(entry->func_body)
            {
                free_node_tree(entry->func_body);
            }

            struct symtab_entry_s *next = entry->next;
            free(entry);
            entry = next;
        }
    }

    free(symtab);
}

/*Debugging the symbol table & functions
* Prints the contents of the local symbol table
* When our shell starts, the local and global symbol tables will refer to the same table. 
* It is only when the shell is about to run a shell function or script file that we have a local table that is different from the global table. 
*/

void dump_local_symtab(void)
{
    struct symtab_s *symtab = symtab_stack.local_symtab;
    int i = 0;
    int indent = symtab->level * 4;

    fprintf(stderr, "%*sSymbol table [Level %d]:\r\n", indent, " ", symtab->level);
    fprintf(stderr, "%*s===========================\r\n", indent, " ");
    fprintf(stderr, "%*s  No               Symbol                    Val\r\n", indent, " ");
    fprintf(stderr, "%*s------ -------------------------------- ------------\r\n", indent, " ");

    int index = 0;

    for (int bucket = 0; bucket < HASH_SIZE; bucket++)
    {
        struct symtab_entry_s *entry = symtab->buckets[bucket];

        while(entry)
        {
            fprintf(stderr, "%*s[%04d] %-32s '%s'\r\n", indent, " ",
                    index++, entry->name, entry->val);
            entry = entry->next;
        }
    }

    fprintf(stderr, "%*s------ -------------------------------- ------------\r\n", indent, " ");
}


/* Add new entry to the local symbol table
* each entry w/ unique kwy
*enusre uniqueness by using the 
*/

struct symtab_entry_s *add_to_symtab(char *symbol)
{
    if(!symbol || symbol[0] == '\0')
    {
        return NULL;
    }

    struct symtab_s *st = symtab_stack.local_symtab;
    struct symtab_entry_s *entry = NULL;

    if((entry = do_lookup(symbol, st)))
    {
        return entry;
    }

    entry = malloc(sizeof(struct symtab_entry_s));

    if(!entry)
    {
        fprintf(stderr, "fatal error: no memory for new symbol table entry\n");
        exit(EXIT_FAILURE);
    }

    memset(entry, 0, sizeof(struct symtab_entry_s));
    entry->name = malloc(strlen(symbol)+1);

    if(!entry->name)
    {
        fprintf(stderr, "fatal error: no memory for new symbol table entry\n");
        exit(EXIT_FAILURE);
    }

    strcpy(entry->name, symbol);

    unsigned int h = hash(symbol);

    entry->next = st->buckets[h];
    st->buckets[h] = entry;

    return entry;
}


/*
*This function frees the memory used by the entry, 
* and adjusts the linked list pointers to remove the entry from the symbol table.
*
*/

int rem_from_symtab(struct symtab_entry_s *entry, struct symtab_s *symtab)
{
    int res = 0;

    if(entry->val)
    {
        free(entry->val);
    }

    if(entry->func_body)
    {
        free_node_tree(entry->func_body);
    }

    free(entry->name);

    unsigned int h = hash(entry->name);
    struct symtab_entry_s *current = symtab->buckets[h];
    struct symtab_entry_s *prev = NULL;

    while(current)
    {
        if(current == entry)
        {
            if(prev)
            {
                prev->next = current->next;
            }
            else
            {
                symtab->buckets[h] = current->next;
            }
            res = 1;
            break;
        }
        prev = current;
        current = current->next;
    }

    free(entry);
    return res;
}


/*unction searches the given symbol table,
*  If the entry's key matches the variable name we're looking for, the function returns the entry.
*Otherwise, If no match is found, we return
*/

struct symtab_entry_s *do_lookup(char *str, struct symtab_s *symtable)
{
    if(!str || !symtable)
    {
        return NULL;
    }

    unsigned int h = hash(str);
    struct symtab_entry_s *entry = symtable->buckets[h];

    while(entry)
    {
        if(strcmp(entry->name, str) == 0)
        {
            return entry;
        }
        entry = entry->next;
    }

    return NULL;
}

/*Similar to above we lookup and return buttt
* The difference here is that func searches the whole stack, starting with the local symbol table.
*/

struct symtab_entry_s *get_symtab_entry(char *str)
{
    int i = symtab_stack.symtab_count-1;

    do
    {
        struct symtab_s *symtab = symtab_stack.symtab_list[i];
        struct symtab_entry_s *entry = do_lookup(str, symtab);

        if(entry)
        {
            return entry;
        }

    } while(--i >= 0);

    return NULL;
}


/*
* This function frees the memory used to store the old entry's value (if one exists). 
* It then creates a copy of the new value and stores it in the symbol table entry.
*/
void symtab_entry_setval(struct symtab_entry_s *entry, char *val)
{
    if(entry->val)
    {
        free(entry->val);
    }

    if(!val)
    {
        entry->val = NULL;
    }
    else
    {
        char *val2 = malloc(strlen(val)+1);

        if(val2)
        {
            strcpy(val2, val);
        }
        else
        {
            fprintf(stderr, "error: no memory for symbol table entry's value\n");
        }

        entry->val = val2;
    }
}

unsigned int hash(char *str)
{
    unsigned long h = 5381;

    while (*str)
    {
        h = ((h << 5) + h) + (unsigned char)*str;
        str++;
    }

    return (unsigned int)(h % HASH_SIZE);
}


//.... Stack functions below ....//

//adds the given symbol table to the stack, and assigns the newly added table as the local symbol table.
void symtab_stack_add(struct symtab_s *symtab)
{
    symtab_stack.symtab_list[symtab_stack.symtab_count++] = symtab;
    symtab_stack.local_symtab = symtab;
}

//creates a new, empty symbol table and pushes it on top of the stack.
struct symtab_s *symtab_stack_push(void)
{
    struct symtab_s *st = new_symtab(++symtab_level);
    symtab_stack_add(st);
    return st;
}

//removes (or pops) the symbol table on top of the stack, adjusting the stack pointers as needed.
struct symtab_s *symtab_stack_pop(void)
{
    if(symtab_stack.symtab_count == 0)
    {
        return NULL;
    }

    struct symtab_s *st = symtab_stack.symtab_list[symtab_stack.symtab_count-1];

    symtab_stack.symtab_list[--symtab_stack.symtab_count] = NULL;
    symtab_level--;

    if(symtab_stack.symtab_count == 0)
    {
        symtab_stack.local_symtab  = NULL;
        symtab_stack.global_symtab = NULL;
    }
    else
    {
        symtab_stack.local_symtab = symtab_stack.symtab_list[symtab_stack.symtab_count-1];
    }

    return st;
}

//return pointers to the local and global symbol tables, respectively.
struct symtab_s *get_local_symtab(void)
{
    return symtab_stack.local_symtab;
}

//return pointers to the local and global symbol tables, respectively.
struct symtab_s *get_global_symtab(void)
{
    return symtab_stack.global_symtab;
}

//returns a pointer to the symbol table stack.
struct symtab_stack_s *get_symtab_stack(void)
{
    return &symtab_stack;
}
