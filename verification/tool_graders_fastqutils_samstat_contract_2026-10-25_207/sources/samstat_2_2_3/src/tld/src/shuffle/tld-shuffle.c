#include "tld-shuffle.h"
#include "../rng/tld-rng.h"

#define SHUFFLE_FUNC(type)                                              \
        int tld_shuffle_##type(type* arr,int n, struct rng_state* rng)  \
        {                                                               \
                int r;                                                  \
                int i,j;                                                \
                type tmp;                                               \
                for (i = 0; i < n - 1; i++) {                           \
                        r = tl_random_int(rng,n);                       \
                        j = i +  r % (n-i);                             \
                        tmp = arr[j];                                   \
                        arr[j] = arr[i];                                \
                        arr[i] = tmp;                                   \
                }                                                       \
                return OK;                                              \
        }


SHUFFLE_FUNC(char)
SHUFFLE_FUNC(int8_t)
SHUFFLE_FUNC(uint8_t)
SHUFFLE_FUNC(int16_t)
SHUFFLE_FUNC(uint16_t)
SHUFFLE_FUNC(int32_t)
SHUFFLE_FUNC(uint32_t)
SHUFFLE_FUNC(int64_t)
SHUFFLE_FUNC(uint64_t)
SHUFFLE_FUNC(float)
SHUFFLE_FUNC(double)
