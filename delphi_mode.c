#include "delphi_mode.h"

int delphi_mode_enabled = 0;

void set_delphi_mode(int enabled)
{
    delphi_mode_enabled = enabled ? 1 : 0;
}

int is_delphi_mode(void)
{
    return delphi_mode_enabled;
}