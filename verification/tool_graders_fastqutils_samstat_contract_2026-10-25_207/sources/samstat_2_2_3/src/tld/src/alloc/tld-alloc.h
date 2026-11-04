#ifndef TLD_ALLOC_H
#define TLD_ALLOC_H

#include "../core/tld-core.h"
#include <string.h>

#define MFREE(p)                                        \
        if (p) {                                        \
                free(p);                                \
                (p) = NULL;                             \
        } else {                                        \
                WARNING_MSG("free on a null pointer");  \
        }

#define MMALLOC(p, size)                                        \
        if ((p) != NULL) {                                      \
                ERROR_MSG("malloc on a nun-null pointer");      \
                goto ERROR;                                     \
        }                                                       \
        if ((size) == 0) {                                      \
                ERROR_MSG("malloc of size %d failed", size);    \
                goto ERROR;                                     \
        }                                                       \
        if (((p) = malloc(size)) == NULL) {                     \
                ERROR_MSG("malloc of size %d failed", size);    \
                goto ERROR;                                     \
        }                                                       \
        memset(p, 0, size);

#define MREALLOC(p, size)                                               \
        do {                                                            \
                void *tmpp;                                             \
                if ((size) == 0) {                                      \
                        ERROR_MSG("malloc of size %d failed", size);    \
                        goto ERROR;                                     \
                }                                                       \
                if ((p) == NULL) {                                      \
                        tmpp = malloc(size);                            \
                } else {                                                \
                        tmpp = realloc((p), (size));                    \
                }                                                       \
                if (tmpp != NULL) {                                     \
                        (p) = tmpp;                                     \
                } else {                                                \
                        ERROR_MSG("realloc for size %d failed", size);  \
                        goto ERROR;                                     \
                }                                                       \
        } while (0)

#define tld_valid_1D(x)                                                 \
        _Generic((x), char ** : 1, int8_t ** : 1, uint8_t ** : 1, int16_t ** : 1, \
                 uint16_t ** : 1, int32_t ** : 1, uint32_t ** : 1, int64_t ** : 1, \
                 uint64_t ** : 1, float ** : 1, double ** : 1, default : 0)

#define tld_valid_2D(x)                                                 \
        _Generic((x), char *** : 1, int8_t *** : 1, uint8_t *** : 1,    \
                 int16_t *** : 1, uint16_t *** : 1, int32_t *** : 1,    \
                 uint32_t *** : 1, int64_t *** : 1, uint64_t *** : 1, float *** : 1, \
                 double *** : 1, default : 0)

#define XARG3(_0, _1, _2, _3, ...) _3
#define NARG3(...) XARG3(__VA_ARGS__, 3, 2, 1, 0)

#define XGALLOC_ARGS_1(a) galloc_too_few()
#define XGALLOC_ARGS_2(a, b)                                            \
        do {                                                            \
                if (!tld_valid_1D((a))) {                               \
                        ERROR_MSG("Wrong pointer type for 1D alloc");   \
                }                                                       \
                *(a) = galloc_hlp(sizeof(__typeof__(**(a))), (b), 0);   \
                if (*(a) == NULL) {                                     \
                        ERROR_MSG("Could not alloc 1D");                \
                }                                                       \
        } while (0);

#define XGALLOC_ARGS_3(a, b, c)                                         \
        do {                                                            \
                if (!tld_valid_2D((a))) {                               \
                        ERROR_MSG("Wrong pointer type for 2D alloc");   \
                }                                                       \
                __typeof__(*(a)) ptr_t = NULL;                          \
                ptr_t = galloc_hlp(sizeof(__typeof__(**(a))), (b), (c)); \
                void *__tld_internal_p = NULL;                          \
                get_ptr(ptr_t, &__tld_internal_p);                                     \
                ptr_t[0] = (__typeof__(**(a)))__tld_internal_p;         \
                for (int i = 1; i < (b); i++) {                         \
                        ptr_t[i] = ptr_t[0] + (c)*i;                    \
                }                                                       \
                *(a) = ptr_t;                                           \
        } while (0);

#define gfree(a) tld_free(a)

#define XXGALLOC_ARGS(N, ...) XGALLOC_ARGS_##N(__VA_ARGS__)
#define XGALLOC_ARGS(N, ...) XXGALLOC_ARGS(N, __VA_ARGS__)
#define GALLOC_ARGS(...) XGALLOC_ARGS(NARG3(__VA_ARGS__), __VA_ARGS__)
#define galloc(...) GALLOC_ARGS(__VA_ARGS__)

tld_external int galloc_too_few(void);
tld_external void *galloc_hlp(size_t tsize, int dim1, int dim2);
tld_external void tld_free(void *p);

tld_external int get_dim1(void *ptr, uint32_t *d);
tld_external int get_dim2(void *ptr, uint32_t *d);
tld_external int get_ptr(void *ptr, void **d);

#endif
