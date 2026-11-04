#include "../core/tld-core.h"
#include "../alloc/tld-alloc.h"

/* Weird but works... */
#include "tpool_internal.h"
#include "tpool_internal.c"

#include <unistd.h>
#include <signal.h>

#define TPOOL_IMPORT
#include "tpool.h"

atomic_int tld_global_stop_run;
pthread_mutex_t tld_global_cond_mutex;
pthread_cond_t tld_global_cond;

static void *pool_worker(void *data);
static int pool_get_tid(tld_thread_pool *p);

static int test_runtime(time_t internal_time,time_t* stop_watch,double maxtime,int* run);

static int setup_signals_and_thread_comms(void);
static void catch_signal(int sig);


int tld_thread_pool_add(tld_thread_pool *p, void (*func_ptr)(tld_thread_pool*,void *,int64_t, int64_t,int), void *data, int64_t start, int64_t end)
{
        /* LOG_MSG("Adding work"); */
        pthread_mutex_lock(&p->lock);
        if(tld_global_stop_run == 1){
                p->stop = 1;
        }
        if(!p->stop){
                /* LOG_MSG("Adding work"); */
                RUN(work_queue_push(p->work, func_ptr, data, start, end));
                pthread_cond_broadcast(&p->work_cond);
        }
        pthread_mutex_unlock(&p->lock);
        return OK;
ERROR:
        return FAIL;
}

void *pool_worker(void *data)
{
        tld_thread_pool*  p = (tld_thread_pool*) data;
        void (*func_ptr)(tld_thread_pool*, void *,int64_t, int64_t, int ) = NULL;
        void* fun_data = NULL;
        const int thread_id = pool_get_tid(p);
        int64_t start;
        int64_t end;
        while(1){

                pthread_mutex_lock(&p->lock);
                /* LOG_MSG("Worker %5d entering holding pattern threads: %d work : %d ",thread_id, p->n_threads, work_queue_haswork(p->work)); */
                while(!work_queue_haswork(p->work) && !p->stop){
                        pthread_cond_wait(&p->work_cond, &p->lock);
                }
                /* LOG_MSG("Unlocked %5d -> stop %d", thread_id, p->stop); */
                if(tld_global_stop_run == 1){
                        p->stop = 1;
                }

                if(p->stop){
                        /* LOG_MSG("Thread %d stopping", thread_id); */
                        break;
                }

                start = 0 ;
                end = 0;
                work_queue_pop(p->work,  &func_ptr, &fun_data, &start, &end);
                p->n_working++;
                pthread_mutex_unlock(&p->lock);

                func_ptr(p,fun_data,start, end, thread_id);

                pthread_mutex_lock(&p->lock);
                p->n_jobs_processed++;
                p->n_working--;
                if(p->maxtime && !p->stop){
                        test_runtime(p->internal_time, &p->stop_watch, p->maxtime, &p->stop);
                        if(p->stop == 1){
                                LOG_MSG("Stopping because of time!");
                                pthread_cond_broadcast(&p->working_cond);
                        }
                }
                if (!p->stop && p->n_working == 0 && !work_queue_haswork(p->work)){
                        pthread_cond_signal(&p->working_cond);
                }
                pthread_mutex_unlock(&p->lock);
        }
        p->n_active_threads--;

        pthread_cond_signal(&p->working_cond);
        pthread_mutex_unlock(&p->lock);

        pthread_exit(0);
        return NULL;
}

int tld_thread_pool_create(tld_thread_pool **pool, double max_time, int n_threads)
{
        tld_thread_pool* p = NULL;
        MMALLOC(p, sizeof(tld_thread_pool));


        if(n_threads < 2){
                n_threads = 2;
        }
        p->work = NULL;
        p->n_threads = n_threads;
        p->n_active_threads = n_threads;
        p->n_jobs_processed = 0;
        p->maxtime = max_time;
        p->n_working = 0;
        /* p->n_working = 0; */

        p->thread_id_map = NULL;
        /* c->done = WORLD_RUN_CONTINUE; */
        galloc(&p->thread_id_map,p->n_threads);
        p->thread_id_idx = 0;
        MMALLOC(p->threads, sizeof(pthread_t) * p->n_threads);


        pthread_mutex_init(&p->lock, NULL);

        pthread_cond_init(&p->work_cond, NULL);
        pthread_cond_init(&p->working_cond, NULL);

        pthread_attr_init(&p->attr);
        pthread_attr_setdetachstate(&p->attr, PTHREAD_CREATE_JOINABLE);


        time(&p->internal_time);
        time(&p->stop_watch);

        p->stop = 0;
        /* p->n_work = 0; */
        RUN(work_queue_alloc(&p->work, 1024));

        /* if(p->maxtime){ */
        /* tld_thread_pool_add(p, sleepy_job,p); */
        /* } */

        for(long t = 0; t < p->n_threads; t++){
                int rc = pthread_create(&p->threads[t], &p->attr, pool_worker,  (void *)p);

                if(rc){
                        ERROR_MSG("ERROR; return code from pthread_create() is %d\n", rc);
                }
                /* LOG_MSG("created thread %d  %ld", t , (uint64_t)p->threads[t]) ; */
        }
        /* LOG_MSG("Setting up comms"); */
        setup_signals_and_thread_comms();


        *pool = p;



        return OK;
ERROR:
        return FAIL;
}

void tld_thread_pool_wait(tld_thread_pool *p)
{
        /* static struct timespec time_to_wait = {0, 0}; */
        if(p){
                pthread_mutex_lock(&p->lock);
                while (1) {
                        /* LOG_MSG("Waiting:"); */

                        /* LOG_MSG("Condition one: !stop && p->n_working: %d %d : %d",!p->stop, work_queue_haswork(p->work), (!p->stop && p->n_active_threads != 0)); */
                        /* LOG_MSG("Condition two:  stop && p->n_threads: %d %d : %d",p->stop, p->n_threads, (p->stop && p->n_threads != 0)); */

                        if((!p->stop &&  p->n_working != 0) || (p->stop && p->n_active_threads != 0)) {
                                /* LOG_MSG("Waiting #################################!!!"); */
                                /* time_to_wait.tv_sec = time(NULL) + 1L; */
                                /* pthread_cond_timedwait(&p->working_cond, &p->lock, &time_to_wait); */
                                pthread_cond_wait(&p->working_cond, &p->lock);
                        }else{
                                break;
                        }
                        /* if(global_stop_run == 1){ */
                                /* p->stop = 1; */
                        /* } */

                }
                pthread_mutex_unlock(&p->lock);
        }
}

void tld_thread_pool_free(tld_thread_pool *p)
{

        if(p){
                pthread_mutex_lock(&p->lock);
                LOG_MSG("Did %d jobs", p->n_jobs_processed);
                /* p->n_work = 0; */
                p->stop = 1;

                pthread_cond_broadcast(&p->work_cond);
                pthread_mutex_unlock(&p->lock);

                /* WAIT;..  */
                tld_thread_pool_wait(p);
                /* LOG_MSG("Active: %d", p->n_active_threads); */
                /* p->n_threads = 8; */
                for(long t = 0; t < p->n_threads; t++) {
                        void *status;
                        /* LOG_MSG("Cancelling thread %d  %ld", t , (uint64_t)p->threads[t]) ; */
                        int rc = pthread_join(p->threads[t], &status);
                        if(rc){
                                WARNING_MSG("ERROR::::: return code from pthread_join() is %d status: %d\n", rc, status );
                        }
                        if(status == PTHREAD_CANCELED){
                                fprintf(stdout,"Main: completed join with thread %ld having a status of %ld (cancelled)\n",t,(long)status);
                        }
                }



                MFREE(p->threads);
                gfree(p->thread_id_map);
                work_queue_free(p->work);
                pthread_mutex_destroy(&p->lock);


                pthread_cond_destroy(&p->work_cond);
                pthread_cond_destroy(&p->working_cond);

                MFREE(p);
        }
}



int test_runtime(time_t internal_time,time_t* stop_watch,double maxtime,int* run)
{
        double diff_t = 0.0;
        time_t cur_time;

        time(&cur_time);
        diff_t = difftime(cur_time , *stop_watch) / 60.0;

        if(diff_t > 1.0){
                diff_t = difftime(cur_time , internal_time) / 60.0;
                /* LOG_MSG("%f minutes have elapsed", diff_t); */
                time(stop_watch);
        }

        diff_t = difftime(cur_time , internal_time) / 60.0;
        /* LOG_MSG("Diff time : %f", diff_t); */
        if(diff_t > maxtime){
                /* LOG_MSG("Allocated time has elapsed!"); */
                *run = 1;
        }
        return OK;
}

int pool_get_tid(tld_thread_pool *p)
{
        int i;
        int64_t tid = (int64_t) pthread_self();
        int ID = -1;
        pthread_mutex_lock(&p->lock);
        for(i = 0; i < p->thread_id_idx;i++){
                if(p->thread_id_map[i] == tid){
                        ID = i;
                        break;
                }
        }
        if(ID == -1){
                ID = p->thread_id_idx;
                p->thread_id_map[p->thread_id_idx] = tid;
                p->thread_id_idx++;
        }
        pthread_mutex_unlock(&p->lock);

        return ID;
}


int setup_signals_and_thread_comms(void)
{
        int status = 0;
        tld_global_stop_run = 0;
        status = pthread_mutex_init(&tld_global_cond_mutex, NULL);
        if(status){
                ERROR_MSG("pthread_mutex_init failed with %d", status);
        }
        status = pthread_cond_init(&tld_global_cond, NULL);
        if(status){
                ERROR_MSG("pthread_cond_init failed with %d", status);
        }
        signal(SIGINT, catch_signal);
        signal(SIGABRT, catch_signal);
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
        tld_global_stop_run = 1;
        pthread_mutex_lock(&tld_global_cond_mutex);
        LOG_MSG("Ohhh am being interupted.... %d ", sig);
        pthread_cond_broadcast(&tld_global_cond);
        pthread_mutex_unlock(&tld_global_cond_mutex);
        n_inter++;
}
