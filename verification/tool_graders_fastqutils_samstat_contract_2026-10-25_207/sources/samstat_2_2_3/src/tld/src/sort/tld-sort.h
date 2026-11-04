#ifndef SORT_H
#define SORT_H

#include "../core/tld-core.h"


#define SORT_HEADER(type)                       \
        int sort_desc_##type(type *a, int len); \
        int sort_asc_##type (type* a, int len);

SORT_HEADER(char)
        SORT_HEADER(int8_t)
        SORT_HEADER(uint8_t)
        SORT_HEADER(int16_t)
        SORT_HEADER(uint16_t)
        SORT_HEADER(int32_t)
        SORT_HEADER(uint32_t)
        SORT_HEADER(int64_t)
        SORT_HEADER(uint64_t)
        SORT_HEADER(float)
        SORT_HEADER(double)


#define TLD_SORT_DESC(A,N) _Generic((A),                                \
                                    char* : sort_desc_char,             \
                                    int8_t* : sort_desc_int8_t,         \
                                    uint8_t* : sort_desc_uint8_t,       \
                                    int16_t* : sort_desc_int16_t,       \
                                    uint16_t* : sort_desc_uint16_t,     \
                                    int32_t *: sort_desc_int32_t,       \
                                    uint32_t* : sort_desc_uint32_t,     \
                                    int64_t* : sort_desc_int64_t,       \
                                    uint64_t*: sort_desc_uint64_t,      \
                                    float* : sort_desc_float,           \
                                    double* : sort_desc_double)(A,N)


#define TLD_SORT_ASC(A,N) _Generic((A),                             \
                                   char* : sort_asc_char,           \
                                   int8_t* : sort_asc_int8_t,       \
                                   uint8_t* : sort_asc_uint8_t,     \
                                   int16_t* : sort_asc_int16_t,     \
                                   uint16_t* : sort_asc_uint16_t,   \
                                   int32_t *: sort_asc_int32_t,     \
                                   uint32_t* : sort_asc_uint32_t,   \
                                   int64_t* : sort_asc_int64_t,     \
                                   uint64_t*: sort_asc_uint64_t,    \
                                   float* : sort_asc_float,         \
                                   double* : sort_asc_double)(A,N)

#endif
