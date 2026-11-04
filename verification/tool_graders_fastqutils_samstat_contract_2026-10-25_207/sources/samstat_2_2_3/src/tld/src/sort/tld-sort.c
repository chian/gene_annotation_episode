#include "tld-sort.h"


#define DESC_FUNC(type)                                             \
        static int cmp_desc_##type (const void *a, const void *b);  \
                                                                    \
        int sort_desc_##type(type *a, int len)                      \
        {                                                           \
                qsort(a, len, sizeof(type), cmp_desc_ ##type);      \
                return OK;                                          \
        }                                                           \
                                                                    \
        int cmp_desc_##type (const void *a, const void *b)          \
        {                                                           \
                const type  *ia = (const type *)a;                  \
                const type  *ib = (const type *)b;                  \
                if(*ia < *ib ){                                     \
                        return 1;                                   \
                }else{                                              \
                        return -1;                                  \
                }                                                   \
        }                                                           \
                                                                    \
        static int cmp_asc_##type (const void *a, const void *b);   \
                                                                    \
        int sort_asc_##type(type *a, int len)                       \
        {                                                           \
                qsort(a, len, sizeof(type), cmp_asc_ ##type);       \
                return OK;                                          \
        }                                                           \
                                                                    \
        int cmp_asc_##type (const void *a, const void *b)           \
        {                                                           \
                const type  *ia = (const type *)a;                  \
                const type  *ib = (const type *)b;                  \
                if(*ia > *ib ){                                     \
                        return 1;                                   \
                }else{                                              \
                        return -1;                                  \
                }                                                   \
        }





DESC_FUNC(char)
DESC_FUNC(int8_t)
DESC_FUNC(uint8_t)
DESC_FUNC(int16_t)
DESC_FUNC(uint16_t)
DESC_FUNC(int32_t)
DESC_FUNC(uint32_t)
DESC_FUNC(int64_t)
DESC_FUNC(uint64_t)
DESC_FUNC(float)
DESC_FUNC(double)
