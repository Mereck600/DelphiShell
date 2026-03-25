#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include "shell.h"
#include "source.h"
#include "parser.h"
#include "executor.h"
#include "delphi_mode.h"
int run_delphi_input(const char *input);


//Main.c is the REPL (Read, Eavluate, Print, loop).
//The shell reads input, parses it and executes it then loops to the next command
//
// if error we exit, if empty we skip input and keep looping
// if exit we exit the shell, otherwise we echo back cmd, free mem and continue w/ loop

int main(int argc, char **argv){
	char *cmd;
    initsh(); //init the symbol table and stack elements

	do{
		//prints the prompt string
		print_prompt1(); 
		
		//Reads the next line of input
		cmd = read_cmd();

		if(!cmd){
			exit(EXIT_SUCCESS);

		}

		if(cmd[0] =='\0' || strcmp(cmd, "\n") == 0){
			free(cmd);
			continue;
		}
		
		if(strcmp(cmd, "exit\n")==0){
			free(cmd);
			break;
			}
		
		// printf("%s\n", cmd);
        //Normal shell should wtill work here and command delphi goes through builtin
        if (is_delphi_mode() && strncmp(cmd, "delphi", 6) != 0) {
            run_delphi_input(cmd);
        } else {
            struct source_s src;
            src.buffer   = cmd;
            src.bufsize  = strlen(cmd);
            src.curpos   = INIT_SRC_POS;
            parse_and_execute(&src);
        }

		
		free(cmd);

				

	}while(1);
	exit(EXIT_SUCCESS);
}


//
//Reading user input
//
//read input from 1024-byte chunk and store input into buffer using malloc
//So subsequent chunks we use realloc if there is error we print the error
//If everything goes well, we copy that chunk into buffer and adjsut our pointers
// we check the backslash to see if there is a code block designated. 
// when we see the escaped newline char, we discard the two characters and continue.
//
char *read_cmd(void)
{
    char buf[1024];
    char *ptr = NULL;
    char ptrlen = 0;

    while(fgets(buf, 1024, stdin))
    {
        int buflen = strlen(buf);

        if(!ptr)
        {
            ptr = malloc(buflen+1);
        }
        else
        {
            char *ptr2 = realloc(ptr, ptrlen+buflen+1);

            if(ptr2)
            {
                ptr = ptr2;
            }
            else
            {
                free(ptr);
                ptr = NULL;
            }
        }

        if(!ptr)
        {
            fprintf(stderr, "error: failed to alloc buffer: %s\n", strerror(errno));
            return NULL;
        }

        strcpy(ptr+ptrlen, buf);

        if(buf[buflen-1] == '\n')
        {
            if(buflen == 1 || buf[buflen-2] != '\\')
            {
                return ptr;
            }

            ptr[ptrlen+buflen-2] = '\0';
            buflen -= 2;
            print_prompt2();
        }

        ptrlen += buflen;
    }

    return ptr;
}

int parse_and_execute(struct source_s *src)
{
    skip_white_spaces(src);

    struct token_s *tok = tokenize(src);

    if(tok == &eof_token)
    {
        return 0;
    }

    while(tok && tok != &eof_token)
    {
        struct node_s *cmd = parse_simple_command(tok);

        if(!cmd)
        {
            break;
        }

        do_simple_command(cmd);
        free_node_tree(cmd);
        tok = tokenize(src);
    }

    return 1;
}
