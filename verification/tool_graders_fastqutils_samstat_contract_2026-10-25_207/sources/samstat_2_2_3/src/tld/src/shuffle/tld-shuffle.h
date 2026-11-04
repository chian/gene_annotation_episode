#ifndef SHUFFLE_H
#define SHUFFLE_H



#include "../rng/tld-rng.h"

#define SHUFFLE_HEADER(type)                        \
        int tld_shuffle_##type(type *a, int len, struct rng_state* rng);

SHUFFLE_HEADER(char)
        SHUFFLE_HEADER(int8_t)
        SHUFFLE_HEADER(uint8_t)
        SHUFFLE_HEADER(int16_t)
        SHUFFLE_HEADER(uint16_t)
        SHUFFLE_HEADER(int32_t)
        SHUFFLE_HEADER(uint32_t)
        SHUFFLE_HEADER(int64_t)
        SHUFFLE_HEADER(uint64_t)
        SHUFFLE_HEADER(float)
        SHUFFLE_HEADER(double)


#define TLD_SHUFFLE(A,N,R) _Generic((A),                                 \
                                    char* : tld_shuffle_char,             \
                                    int8_t* : tld_shuffle_int8_t,         \
                                    uint8_t* : tld_shuffle_uint8_t,       \
                                    int16_t* : tld_shuffle_int16_t,       \
                                    uint16_t* : tld_shuffle_uint16_t,     \
                                    int32_t *: tld_shuffle_int32_t,       \
                                    uint32_t* : tld_shuffle_uint32_t,     \
                                    int64_t* : tld_shuffle_int64_t,       \
                                    uint64_t*: tld_shuffle_uint64_t,      \
                                    float* : tld_shuffle_float,           \
                                    double* : tld_shuffle_double)(A,N,R)


#endif
