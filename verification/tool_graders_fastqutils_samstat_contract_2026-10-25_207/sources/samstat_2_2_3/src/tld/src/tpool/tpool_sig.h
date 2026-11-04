#ifndef TPOOL_SIG_H
#define TPOOL_SIG_H

#include "../core/tld-core.h"
#include <unistd.h>
#include <stdatomic.h>
#include <signal.h>

tld_external atomic_int global_stop_run;

tld_external pthread_mutex_t global_cond_mutex;
tld_external  pthread_cond_t global_cond;


tld_external int setup_signals_and_thread_comms(void);
tld_external void catch_signal(int sig);


#endif
