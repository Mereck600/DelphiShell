#include <stdlib.h>
#include "../shell.h"

int shell_exit(int argc, char **argv)
{
    int status = 0;

    if(argc > 1)
    {
        status = atoi(argv[1]);
    }

    exit(status);
}
