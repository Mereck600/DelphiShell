#include <stdio.h>
#include <string.h>
#include "../shell.h"
#include "../delphi_mode.h"

int delphi(int argc, char **argv)
{
    if (argc == 1) {
        set_delphi_mode(!is_delphi_mode());
    } else if (argc == 2) {
        if (strcmp(argv[1], "on") == 0) {
            set_delphi_mode(1);
        } else if (strcmp(argv[1], "off") == 0) {
            set_delphi_mode(0);
        } else {
            fprintf(stderr, "usage: delphi [on|off]\n");
            return 1;
        }
    } else {
        fprintf(stderr, "usage: delphi [on|off]\n");
        return 1;
    }

    if (is_delphi_mode()) {
        printf("[Delphi mode enabled]\n");
    } else {
        printf("[Delphi mode disabled]\n");
    }

    return 0;
}