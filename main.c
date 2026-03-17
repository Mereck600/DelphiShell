#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include "shell.h"


//Main.c is the REPL (Read, Eavluate, Print, loop).
//The shell reads input, parses it and executes it then loops to the next command
//
// if error we exit, if empty we skip input and keep looping
// if exit we exit the shell, otherwise we echo back cmd, free mem and continue w/ loop

int main(int argc, char **argv){
	char *cmd;

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
		
		printf("%s\n", cmd);
		
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
