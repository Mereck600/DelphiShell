#include <stdio.h>
#include "shell.h"
/*
 * Prompt string handling, PS0-PS4
 * These are here to convey certain messages to users
 * */

//Prints the first prompt string when waiting for user input
void print_prompt1(void){
	fprintf(stderr, "$");
	
}

// Prints the sec promt string for multi line commmands
void print_prompt2(void){
	fprintf(stderr, "> ");
}


