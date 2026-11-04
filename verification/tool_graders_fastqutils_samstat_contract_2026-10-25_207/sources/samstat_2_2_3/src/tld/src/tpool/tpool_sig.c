#include "../core/tld-core.h"

#include <pthread.h>
#include "./tpool_sig.h"

int setup_signals_and_thread_comms(void)
{
        int status = 0;
        global_stop_run = 0;
        status = pthread_mutex_init(&global_cond_mutex, NULL);
        if(status){
                ERROR_MSG("pthread_mutex_init failed with %d", status);
        }
        status = pthread_cond_init(&global_cond, NULL);
        if(status){
                ERROR_MSG("pthread_cond_init failed with %d", status);
        }
        signal(SIGINT, catch_signal);
        signal(SIGABRT, catch_signal);
        LOG_MSG("Set up signals.");
        return OK;
ERROR:
        return FAIL;
}

void catch_signal(int sig)
{
        static int n_inter = 0;
        LOG_MSG("Interrupt!!");
        if(n_inter == 5){
                LOG_MSG("Caught five interrupts - exiting");
                exit(EXIT_SUCCESS);
        }
        global_stop_run = 1;
        pthread_mutex_lock(&global_cond_mutex);
        LOG_MSG("Ohhh am being interupted....");
        pthread_cond_broadcast(&global_cond);       /* signal condition */
        pthread_mutex_unlock(&global_cond_mutex);
        printf("Caught signal %d\n", sig);
        LOG_MSG("Interupt = %d", global_stop_run);
        n_inter++;
}
