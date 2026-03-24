#include <stdio.h>
#include "shell.h"
#include "symtab/symtab.h"
//TODO: implement the print_prompt2 function it should be simmilar to p_p1

/*
 * Prompt string handling, PS0-PS4
 * These are here to convey certain messages to users
 * */


//  checks if there is a symbol table entry with the name PS1. 
//  If there is, we use that entry's value to print the first prompt string.
//   Otherwise, we use our default builtin value, which is $
void print_prompt1(void)
{   
    struct symtab_entry_s *entry = get_symtab_entry("PS1");

    if(entry && entry->val)
    {
        fprintf(stderr, "%s", entry->val);
    }
    else
    {
        fprintf(stderr, "$ ");
    }
}

// Prints the sec promt string for multi line commmands
void print_prompt2(void)
{
    struct symtab_entry_s *entry = get_symtab_entry("PS2");

    if(entry && entry->val)
    {
        fprintf(stderr, "%s", entry->val);
    }
    else
    {
        fprintf(stderr, "> ");
    }
}


