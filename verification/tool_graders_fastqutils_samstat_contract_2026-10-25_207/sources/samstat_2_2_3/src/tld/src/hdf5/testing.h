#ifndef TLHDF5WRAP_H
#define TLHDF5WRAP_H



#include "stdint.h"
#include "../core/tld-core.h"
#include "tld-hdf5_struct.h"
#include "tld-hdf5_utils.h"

typedef struct hdf5_data hdf5_data;

struct hdf5_data;


tld_external int tldhdf5_open_file(hdf5_data** h, char* filename);
tld_external int tlfhdf5_close_file(struct hdf5_data **h);

tld_external int hdf5_prepare_read(struct hdf5_data *hdf5_data, char *group, char *name);
tld_external int hdf5_compare_data_types(struct hdf5_data *hdf5_data);
tld_external int hdf5_finalise_read(struct hdf5_data *hdf5_data);

tld_external int tld_h5D_read_wrap(struct hdf5_data *hdf5_data); /* really low level  */

tld_external int hdf5_read(struct hdf5_data *hdf5_data, char *group, char *name, int **data);
tld_external int hdf5_write(struct hdf5_data *hdf5_data, char *group,
                            char *name, void *data);


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


#define SETTYPR(t)                                      \
        int set_type_ ## t(hid_t* type);

SETTYPR(char)
SETTYPR(int8_t)
SETTYPR(uint8_t)
SETTYPR(int16_t)
SETTYPR(uint16_t)
SETTYPR(int32_t)
SETTYPR(uint32_t)
SETTYPR(int64_t)
SETTYPR(uint64_t)
SETTYPR(float)
SETTYPR(double)

int set_type_unknown(hid_t *type);

#undef SETTYPR

#define HDFWRAP_SET_TYPE(P,T) _Generic((P),                             \
                                       char: set_type_char,             \
                                       char*: set_type_char,            \
                                       char**: set_type_char,           \
                                       char***: set_type_char,          \
                                       int8_t: set_type_int8_t,         \
                                       int8_t*: set_type_int8_t,        \
                                       int8_t**: set_type_int8_t,       \
                                       int8_t***: set_type_int8_t,      \
                                       uint8_t: set_type_uint8_t,       \
                                       uint8_t*: set_type_uint8_t,      \
                                       uint8_t**: set_type_uint8_t,     \
                                       uint8_t***: set_type_uint8_t,    \
                                       int16_t: set_type_int16_t,       \
                                       int16_t*: set_type_int16_t,      \
                                       int16_t**: set_type_int16_t,     \
                                       int16_t***: set_type_int16_t,    \
                                       uint16_t: set_type_uint16_t,     \
                                       uint16_t*: set_type_uint16_t,    \
                                       uint16_t**: set_type_uint16_t,   \
                                       uint16_t***: set_type_uint16_t,  \
                                       int32_t: set_type_int32_t,       \
                                       int32_t*: set_type_int32_t,      \
                                       int32_t**: set_type_int32_t,     \
                                       int32_t***: set_type_int32_t,    \
                                       uint32_t: set_type_uint32_t,     \
                                       uint32_t*: set_type_uint32_t,    \
                                       uint32_t**: set_type_uint32_t,   \
                                       uint32_t***: set_type_uint32_t,  \
                                       int64_t: set_type_int64_t,       \
                                       int64_t*: set_type_int64_t,      \
                                       int64_t**: set_type_int64_t,     \
                                       int64_t***: set_type_int64_t,    \
                                       uint64_t: set_type_uint64_t,     \
                                       uint64_t*: set_type_uint64_t,    \
                                       uint64_t**: set_type_uint64_t,   \
                                       uint64_t***: set_type_uint64_t,  \
                                       float: set_type_float,           \
                                       float*: set_type_float,          \
                                       float**: set_type_float,         \
                                       float***: set_type_float,        \
                                       double: set_type_double,         \
                                       double*: set_type_double,        \
                                       double**: set_type_double,       \
                                       double***: set_type_double,      \
                                       default: set_type_unknown        \
                )(T)

#define HDF_READ_DATA(F, G, N, V)                                   \
        do {                                                        \
                RUN(hdf5_prepare_read(F, G, N));                    \
                LOG_MSG("RANK:%d", F->rank);                        \
                HDFWRAP_SET_TYPE(V, &F->native_type);               \
                RUN(hdf5_compare_data_types(F));                    \
                if(F->rank == 1){                                   \
                        galloc(V,(int)F->dim[0]);                   \
                }else{                                              \
                        galloc(V,(int)F->dim[0],(int) F->dim[1]);   \
                }                                                   \
                void*__tld_internal_ptr = NULL;                     \
                HDFWRAP_START_GALLOC(*(V), &__tld_internal_ptr);    \
                F->data = __tld_internal_ptr;                       \
                tld_h5D_read_wrap(F);                               \
                hdf5_finalise_read(F);                              \
        }while (0)


#define HDF_READ_VALUE(F, G, N, V)                    \
        do {                                            \
                RUN(hdf5_prepare_read(F, G, N));        \
                HDFWRAP_SET_TYPE(V, &F->native_type);   \
                RUN(hdf5_compare_data_types(F));        \
                F->data = (void*)V;                     \
                tld_h5D_read_wrap(F);                   \
                hdf5_finalise_read(F);                  \
        }while (0)


#define HDF_WRITE_DATA(F, G, N, V)                      \
        do {                                            \
                void *ptr = NULL;                       \
                HDFWRAP_SET_TYPE(V, &(F)->native_type); \
                LOG_MSG("%d", HDFWRAP_GET_DIM(V));      \
                if(HDFWRAP_GET_DIM(V) == 1){            \
                        F->dim[0] = 1;                  \
                        F->dim[1] = 0;                  \
                        F->chunk_dim[0] = 1;            \
                        F->chunk_dim[1] = 0;            \
                        F->rank = 1;                    \
                        ptr = V;                        \
                }else{                                  \
                        uint32_t d1 = 0U;               \
                        uint32_t d2 = 0U;               \
                        HDFWRAP_START_GALLOC(*(V), &ptr);   \
                        RUN(get_dim1((void *)*(V), &d1));  \
                        RUN(get_dim2((void *)*(V), &d2));        \
                        F->dim[0] = d1;                 \
                        F->dim[1] = d2;                 \
                        F->chunk_dim[0] = d1;           \
                        F->chunk_dim[1] = d2;           \
                        F->rank = 1;                    \
                        if (d2) {                       \
                                F->rank = 2;            \
                        }                               \
                }                                       \
                RUN(hdf5_write(F, G, N,ptr ));          \
        }while (0)



#endif
