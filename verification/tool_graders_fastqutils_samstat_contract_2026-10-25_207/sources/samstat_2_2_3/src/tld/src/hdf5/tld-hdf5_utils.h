#ifndef TLD_HDF5_UTILS_H
#define TLD_HDF5_UTILS_H

#include "stdint.h"


typedef int64_t hid_t;

#ifdef TLDHDF5_UTILS_IMPORT
#define EXTERN
#else
#define EXTERN extern
#endif

#define HDFWRAP_GET_DIM(T) _Generic((T),            \
                                    char: 0,        \
                                    char*: 1,       \
                                    char**: 2,      \
                                    char***: 3,     \
                                    int8_t: 0,      \
                                    int8_t*:1,      \
                                    int8_t**:2,     \
                                    int8_t***:3,    \
                                    uint8_t:0,      \
                                    uint8_t*:1,     \
                                    uint8_t**:2,    \
                                    uint8_t***:3,   \
                                    int16_t:0,      \
                                    int16_t*:1,     \
                                    int16_t**:2,    \
                                    int16_t***:3,   \
                                    uint16_t:0,     \
                                    uint16_t*:1,    \
                                    uint16_t**:2,   \
                                    uint16_t***:3,  \
                                    int32_t:0,      \
                                    int32_t*:1,     \
                                    int32_t**:2,    \
                                    int32_t***:3,   \
                                    uint32_t:0,     \
                                    uint32_t*:1,    \
                                    uint32_t**:2,   \
                                    uint32_t***:3,  \
                                    int64_t:0,      \
                                    int64_t*:1,     \
                                    int64_t**:2,    \
                                    int64_t***:3,   \
                                    uint64_t:0,     \
                                    uint64_t*:1,    \
                                    uint64_t**:2,   \
                                    uint64_t***:3,  \
                                    float:0,        \
                                    float*:1,       \
                                    float**:2,      \
                                    float***:3,     \
                                    double:0,       \
                                    double*:1,      \
                                    double**:2,     \
                                    double***:3,    \
                                    default: -1     \
                )

/*
  These functions determine the pointer to
   the block of memory to be written to hdf5.
 */
#define STARTOF_DATA(type)                                      \
        int startof_galloc_ ##type(type x, void** ptr);         \
        int startof_galloc_ ##type##_s(type* x, void** ptr);    \
        int startof_galloc_ ##type##_ss(type** x, void** ptr);

STARTOF_DATA(char)
STARTOF_DATA(int8_t)
STARTOF_DATA(uint8_t)
STARTOF_DATA(int16_t)
STARTOF_DATA(uint16_t)
STARTOF_DATA(int32_t)
STARTOF_DATA(uint32_t)
STARTOF_DATA(int64_t)
STARTOF_DATA(uint64_t)
STARTOF_DATA(float)
STARTOF_DATA(double)

int startof_galloc_unknown(void* x, void** ptr);

#undef STARTOF_DATA

#define HDFWRAP_START_GALLOC(P,T) _Generic((P),                         \
                                           char: startof_galloc_char,   \
                                           char*: startof_galloc_char_s, \
                                           char**: startof_galloc_char_ss, \
                                           int8_t: startof_galloc_int8_t, \
                                           int8_t*: startof_galloc_int8_t_s, \
                                           int8_t**: startof_galloc_int8_t_ss, \
                                           uint8_t: startof_galloc_uint8_t, \
                                           uint8_t*: startof_galloc_uint8_t_s, \
                                           uint8_t**: startof_galloc_uint8_t_ss, \
                                           int16_t: startof_galloc_int16_t, \
                                           int16_t*: startof_galloc_int16_t_s, \
                                           int16_t**: startof_galloc_int16_t_ss, \
                                           uint16_t: startof_galloc_uint16_t, \
                                           uint16_t*: startof_galloc_uint16_t_s, \
                                           uint16_t**: startof_galloc_uint16_t_ss, \
                                           int32_t: startof_galloc_int32_t, \
                                           int32_t*: startof_galloc_int32_t_s, \
                                           int32_t**: startof_galloc_int32_t_ss, \
                                           uint32_t: startof_galloc_uint32_t, \
                                           uint32_t*: startof_galloc_uint32_t_s, \
                                           uint32_t**: startof_galloc_uint32_t_ss, \
                                           int64_t: startof_galloc_int64_t, \
                                           int64_t*: startof_galloc_int64_t_s, \
                                           int64_t**: startof_galloc_int64_t_ss, \
                                           uint64_t: startof_galloc_uint64_t, \
                                           uint64_t*: startof_galloc_uint64_t_s, \
                                           uint64_t**: startof_galloc_uint64_t_ss, \
                                           float: startof_galloc_float, \
                                           float*: startof_galloc_float_s, \
                                           float**: startof_galloc_float_ss, \
                                           double: startof_galloc_double, \
                                           double*: startof_galloc_double_s, \
                                           double**: startof_galloc_double_ss, \
                                           default: startof_galloc_unknown \
                )(P,T)




#undef TLDHDF5_UTILS_IMPORT
#undef EXTERN


#endif
