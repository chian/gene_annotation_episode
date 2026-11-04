#ifndef TLD_TIMING_H
#define TLD_TIMING_H
#include "../core/tld-core.h"

tld_external void set_exec_time(int end);

#define TLD_START_TIMER set_exec_time(0);
#define TLD_END_TIMER set_exec_time(1);



#endif
