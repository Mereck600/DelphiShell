#ifndef SOURCE_H
#define SOURCE_H

#define EOF             (-1)
#define ERRCHAR         ( 0)

#define INIT_SRC_POS    (-2)

struct source_s
{   
    char *buffer;       /* the input text */
    long bufsize;       /* size of the input text */
    long  curpos;       /* absolute char position in source */
};

char next_char(struct source_s *src);
void unget_char(struct source_s *src); //function returns (or ungets) the last character we've retrieved from input, back to the input source. It does this by simply manipulating the source structure's pointers.
char peek_char(struct source_s *src); // returns the following input character. When we reach the last character in input, the function returns the special character in source.h
void skip_white_spaces(struct source_s *src);

#endif