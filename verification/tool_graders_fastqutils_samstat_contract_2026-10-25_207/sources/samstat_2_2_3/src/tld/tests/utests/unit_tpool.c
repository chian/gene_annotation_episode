#include "tld.h"

#include <unistd.h>

/* #include "tpool_internal.h" */

static void add(tld_thread_pool* p, void *data,int64_t start, int64_t end, int thread_id);
/* static void sub(tld_thread_pool* p, void *data, int thread_id); */

int test_queue(void);
int test_pool(void);
int main(void)
{
        LOG_MSG("Hello pool");
        RUN(test_pool());
        /* RUN(test_queue()); */
        /* RUN(test_pool()); */
        return EXIT_SUCCESS;
ERROR:
        return EXIT_SUCCESS;
}

int test_pool(void)
{
        tld_thread_pool* pool = NULL;
        tld_thread_pool* pool2 = NULL;
        int* array = NULL;
        galloc(&array, 64);

        for(int i = 0; i < 64;i++){
                array[i] = i;
        }
        LOG_MSG("Running threadpool for 15 seconds...");
        tld_thread_pool_create(&pool,0.25, 4);

        LOG_MSG("Running threadpool for 15 seconds...");
        tld_thread_pool_create(&pool2,0.25, 4);
        /* tld_thread_pool_start(pool); */

        /* LOG_MSG("Got here"); */
        for(int c = 0; c < 5;c++){

                for(int i = 0; i < 64;i++){
                        /* sleep(5); */
                        if(i % 1){
                                tld_thread_pool_add(pool, add, array, i, i+1 );
                        }else{
                                tld_thread_pool_add(pool2, add, array, i, i+1 );
                        }
                }
                /* LOG_MSG("Got here - sleep 5"); */
                /* tld_thread_pool_stop(pool); */

                tld_thread_pool_wait(pool);
                tld_thread_pool_wait(pool2);

                LOG_MSG("The wait is over");
        }

        for(int i = 0; i < 64;i++){
                fprintf(stdout,"%d %d\n", i, array[i]);
                /* add(array[i]); */
                /* fprintf(stdout,"%d %d\n", i, array[i]); */

        }
        exit(0);

        for(int i = 0; i < 64;i++){
                /* sleep(5); */

                tld_thread_pool_add(pool, add, &array[i], 0, 0 );
                tld_thread_pool_add(pool, add, &array[i], 0, 0 );
                tld_thread_pool_add(pool, add, &array[i], 0, 0 );
                tld_thread_pool_add(pool, add, &array[i], 0, 0 );
                tld_thread_pool_add(pool, add, &array[i], 0, 0 );
        }

        tld_thread_pool_wait(pool);

        LOG_MSG("The 2nd wait is over active threads: %d", pool->n_active_threads);
        for(int i = 0; i < 64;i++){
                fprintf(stdout,"%d %d\n", i, array[i]);
                /* add(array[i]); */
                /* fprintf(stdout,"%d %d\n", i, array[i]); */

        }


        tld_thread_pool_free(pool);
        gfree(array);
        return OK;
ERROR:
        return FAIL;
}

/* int test_queue(void) */
/* { */

/*         struct work_queue* w = NULL; */
/*         struct rng_state* rng = NULL; */


/*         int number = 100; */

/*         RUN(init_rng(&rng, 0)); */
/*         RUN(work_queue_alloc(&w, 10)); */

/*         for(int i = 0;i < 1245;i++){ */
/*                 double r = tl_random_double(rng); */
/*                 if(r < 0.5){ */
/*                         work_queue_push(w, add, &number ) ; */
/*                 }else{ */
/*                         work_queue_push(w, sub, &number ) ; */
/*                 } */
/*         } */
/*         void (*func_ptr)(tld_thread_pool*,void *,int) = NULL; */
/*         void* data = NULL; */

/*         while(work_queue_haswork(w)){ */
/*                 work_queue_pop(w,  &func_ptr, &data); */
/*                 func_ptr(NULL,data,0); */
/*         } */

/*         LOG_MSG("OPutput : %d", number); */
/*         work_queue_free(w); */

/*         free_rng(rng); */
/*         return OK; */
/* ERROR: */
/*         return FAIL; */
/* } */

#define UNUSED(expr) do { (void)(expr); } while (0)
void add(tld_thread_pool*p,void *data,int64_t start, int64_t end, int thread_id)
{
        int* array = (int*) data;

        UNUSED(thread_id);
        UNUSED(p);
        /* thread_id+= 1; */
        sleep(10.0);

        for(int i = start; i < end;i++){
                array[i] ++;
        }

        /* LOG_MSG("Thread %d doing stuff", thread_id); */
        /* int sum = 0; */
        /* for(int i = 0;i < 1;i++){ */
        /*         sum += i; */
        /*         /\* sum /= thread_id; *\/ */
        /*         /\* sum = sum * sum; *\/ */
        /*         sum = sum  % 65536; */
        /* } */

        /* tld_thread_pool_add(p, add, data,start, end); */


}
#undef UNUSED

/* void sub(tld_thread_pool*p,void *data,int thread_id) */
/* { */
/*         int* num = (int*) data; */
/*         LOG_MSG("Thread %d doing stuff", thread_id); */
/*         *num = *num - 1; */
/* } */
