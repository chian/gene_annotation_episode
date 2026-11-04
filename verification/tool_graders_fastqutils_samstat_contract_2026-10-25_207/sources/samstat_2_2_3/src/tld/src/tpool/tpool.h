#ifndef TPOOL_H
#define TPOOL_H
#include "../core/tld-core.h"
#include <pthread.h>
#include <stdint.h>
#include <stdatomic.h>
struct work_queue;

tld_external atomic_int tld_global_stop_run;
tld_external pthread_mutex_t tld_global_cond_mutex;
tld_external  pthread_cond_t tld_global_cond;



typedef struct tld_thread_pool {
        struct work_queue* work;
        int n_threads;
        int n_active_threads;
        int n_jobs_processed;
        /* Pausing */
        pthread_mutex_t lock;

        pthread_cond_t work_cond;
        pthread_cond_t working_cond;
        pthread_attr_t attr;

        pthread_t* threads;
        int64_t* thread_id_map;
        int thread_id_idx;
        int n_working;
        /* int n_work; */
        int stop;
        double maxtime;
        time_t internal_time;
        time_t stop_watch;
        /* void (*function_ptr)(void*); */

} tld_thread_pool;

tld_external int tld_thread_pool_add(tld_thread_pool *p, void (*func_ptr)(tld_thread_pool*,void *,int64_t, int64_t,int), void *data, int64_t start, int64_t end);
tld_external int  tld_thread_pool_create(tld_thread_pool **pool, double max_time, int n_threads);
tld_external void tld_thread_pool_wait(tld_thread_pool *p);
tld_external void tld_thread_pool_free(tld_thread_pool *p);



#endif
