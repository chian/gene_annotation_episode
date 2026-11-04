
/* #include "tld.h" */
#include "../core/tld-core.h"
#include "../alloc/tld-alloc.h"
#define TPOOL_INTERNAL_IMPORT
#include "tpool_internal.h"

static int  work_item_alloc(struct work_item **work);
static void work_item_free(struct work_item *w);
static int work_queue_add_storage(struct work_queue *q, int size);

int work_queue_haswork(struct work_queue *q)
{
        if(q->head != NULL){
                return 1;
        }
        return 0;
}

int work_queue_push(struct work_queue *q, void (*func_ptr)(tld_thread_pool*, void *,int64_t, int64_t,int), void *data, int64_t start, int64_t end)
{
        struct work_item* new = NULL;

        if(q->store == NULL){
                RUN(work_queue_add_storage(q, 1024));
        }

        new = q->store;

        q->store = q->store->next;

        new->next = NULL;

        new->func_ptr = func_ptr;
        new->data = data;
        new->status = WORK_TODO;
        new->start = start;
        new->end = end;

        if(q->head == NULL){
                q->tail = new;
                q->head = new;
        }else{
                q->tail->next = new;
                q->tail = q->tail->next;
        }
        /* new->next = q->head; */

        /* q->head = new; */
        /* if(q->tail == NULL){ */
                /* q->tail = q->head; */
        /* } */
        /* q->head  */

        /* q->n++; */

        /* if(q->n == q->n_alloc){ */
        /*         RUN(work_queue_expand(q, 0)); */
        /* } */
        /* tmp = q->l[q->n]; */

        /* tmp->data = data; */
        /* tmp->func_ptr = func_ptr; */
        /* tmp->status = WORK_TODO; */
        /* LOG_MSG("Added: %d", q->n); */
        /* LOG_MSG("Added %5d : %p %p", q->n, tmp->func_ptr, tmp->data); */
        return OK;
ERROR:
        return FAIL;
}

int work_queue_pop(struct work_queue *q, void (**func_ptr)(tld_thread_pool*,void *, int64_t, int64_t , int), void **data,int64_t* start, int64_t* end)
{


        struct work_item* tmp = NULL;

        if(q->head == NULL){
                WARNING_MSG("Queue is empty!");
                return OK;
        }

        tmp = q->head;



        *func_ptr = tmp->func_ptr;
        *data = tmp->data;
        *start = tmp->start;
        *end = tmp->end;
        q->head = tmp->next;

        tmp->next = q->store;
        q->store = tmp;
        /* work_item_free(tmp); */

        /* q->head =  */


        /* if(q->n >= 0){ */
        /*         tmp = q->l[q->n]; */
        /*         *func_ptr = tmp->func_ptr; */
        /*         *data = tmp->data; */
        /*         /\* LOG_MSG("taking:  %5d : %p %p", q->n, tmp->func_ptr, tmp->data); *\/ */
        /*         q->n--; */
        /* } */
        /* LOG_MSG("Taking on work %d", q->n+1); */
        return OK;
}


int work_queue_add_storage(struct work_queue *q, int size)
{
        struct work_item* n = NULL;
        if(q->store == NULL){
                RUN(work_item_alloc(&n));
                q->store = n;
        }
        for(int i = 0; i < size;i++){
                RUN(work_item_alloc(&n));
                n->next = q->store;
                q->store = n;
        }
        return OK;
ERROR:
        return FAIL;
}

int work_queue_alloc(struct work_queue **queue, int size)
{
        struct work_queue* q = NULL;

        MMALLOC(q, sizeof(struct work_queue));

        q->n_alloc = size;
        q->n = -1;
        q->l = NULL;

        q->store = NULL;
        q->head = NULL;
        q->tail = NULL;

        RUN(work_queue_add_storage(q, q->n_alloc));

        /* MMALLOC(q->l, sizeof(struct work_item*) * q->n_alloc); */
        /* for(int i = 0; i < q->n_alloc;i++){ */
        /*         q->l[i] = NULL; */
        /*         RUN(work_item_alloc(&q->l[i])); */
        /* } */

        *queue = q;
        return OK;
ERROR:
        work_queue_free(q);
        return FAIL;
}

int work_queue_expand(struct work_queue *q, int add)
{
        ASSERT(q != NULL,"No work queue");
        int old_size;
        if(add == 0){
                add = q->n_alloc/ 2;
        }


        old_size = q->n_alloc;
        q->n_alloc += add;

        MREALLOC(q->l, sizeof(struct work_item*) * q->n_alloc);
        for(int i = old_size; i < q->n_alloc;i++){
                q->l[i] = NULL;
                RUN(work_item_alloc(&q->l[i]));
        }
        return OK;
ERROR:
        work_queue_free(q);
        return FAIL;
}

void work_queue_free(struct work_queue *q)
{
        if(q){
                struct work_item* n = NULL;
                struct work_item* tmp = NULL;
                n = q->head;
                while(n){
                        tmp = n;
                        n = n->next;
                        work_item_free(tmp);
                }

                n = q->store;
                while(n){
                        tmp = n;
                        n = n->next;
                        work_item_free(tmp);
                }

                /* for(int i = 0; i < q->n_alloc;i++){ */
                /*         work_item_free(q->l[i]); */
                /* } */
                /* MFREE(q->l); */
                MFREE(q);
        }
}

int work_item_alloc(struct work_item **work)
{
        struct work_item* w = NULL;
        MMALLOC(w, sizeof(struct work_item));
        w->next = NULL;
        w->func_ptr = NULL;
        w->start = 0;
        w->end = 0;
        w->status = WORK_EMPTY;
        *work = w;
        return OK;
ERROR:
        return FAIL;
}

void work_item_free(struct work_item *w)
{
        if(w){
                MFREE(w);
        }
}
