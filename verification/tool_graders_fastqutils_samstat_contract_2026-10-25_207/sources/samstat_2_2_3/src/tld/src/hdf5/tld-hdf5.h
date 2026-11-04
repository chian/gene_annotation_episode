#ifndef TLHDF5_H
#define TLHDF5_H

#include <hdf5.h>
#include <stdint.h>

#ifdef TLHDF5_IMPORT
#define EXTERN
#else
#define EXTERN extern
#endif

/* struct hdf5_group_names{ */
/*         char** names; */
/*         int num_names; */
/*         int name_length; */
/*         int num_names_mem; */
/* }; */


/* struct hdf5_data{ */
/*         char dataset_name[TLD_HDF5_MAX_NAME_LEN]; */
/*         char group_name[TLD_HDF5_MAX_NAME_LEN]; */
/*         char file_name[TLD_HDF5_MAX_NAME_LEN]; */
/*         char tmp_name[TLD_HDF5_MAX_NAME_LEN]; */

/*         hsize_t dim[2]; */
/*         hsize_t chunk_dim[2]; */
/*         /\* struct hdf5_group_names* grp_names; *\/ */
/*         //struct hdf5_attribute** attr; */
/*         void* data; */
/*         //int num_attr; */
/*         //int num_attr_mem; */
/*         int rank; */

/*         hid_t fapl; */
/*         hid_t file; */
/*         hid_t group; */

/*         hid_t plist; */
/*         hid_t dataset; */

/*         hid_t attribute_id; */
/*         hid_t attr_dataspace_id; */

/*         hid_t datatype; */
/*         hid_t dataspace; */
/*         hid_t datatype_read; */
/*         herr_t status; */
/* }; */


/* This is an attempt to make reading to / from hdf5 files simpler */

/*
   Read / writing is done via these MACROS:

HDF_WRITE_DATA(file handler, path, name, data)
HDF_READ_DATA(file handler, path, name, pointer to where the data should go)
HDF_WRITE_ATTRIBUTE(file handler, path, name, attribute)
HDF_READ_ATTRIBUTE(file handler, path, name, pointer to where the attribute value should go)

In all these examples the 'path' should start with '/' and have no trailing '/'. For example:

/
/group1
/group1/subdir

The data type to be used in the hdf5 file is determined via C11 generic functions

   to open a file:

   open_hdf5_file(file hander, <filename>)

   close:
   close_hdf5_file(file hander,)

 */

struct hdf5_data;

EXTERN int tld_hdf5_open_file(struct hdf5_data** h, char* filename);
EXTERN int tld_hdf5_close_file(struct hdf5_data** h);

//EXTERN int search(struct hdf5_data* hdf5_data);
EXTERN int hdf5wrap_search(struct hdf5_data* hdf5_data,char* target, char** location);


#define ADD_DATA_DEF(type)                                              \
        EXTERN int tld_hdf5_add_0D_dataset_ ##type (struct hdf5_data* hdf5_data, char* group, char* name, type data); \
        EXTERN int tld_hdf5_add_1D_dataset_ ##type (struct hdf5_data* hdf5_data, char* group, char* name, type* data); \
        EXTERN int tld_hdf5_add_2D_dataset_ ##type (struct hdf5_data* hdf5_data, char* group, char* name, type** data);

ADD_DATA_DEF(char)
ADD_DATA_DEF(int8_t)
ADD_DATA_DEF(uint8_t)
ADD_DATA_DEF(int16_t)
ADD_DATA_DEF(uint16_t)
ADD_DATA_DEF(int32_t)
ADD_DATA_DEF(uint32_t)
ADD_DATA_DEF(int64_t)
ADD_DATA_DEF(uint64_t)
ADD_DATA_DEF(float)
ADD_DATA_DEF(double)

#undef ADD_DATA_DEF


#define HDF_WRITE_DATA(F,G,N,V) _Generic((V),                       \
                                             char: tld_hdf5_add_0D_dataset_char, \
                                             char*: tld_hdf5_add_1D_dataset_char, \
                                             char**: tld_hdf5_add_2D_dataset_char, \
                                             int8_t: tld_hdf5_add_0D_dataset_int8_t, \
                                             int8_t*: tld_hdf5_add_1D_dataset_int8_t, \
                                             int8_t**: tld_hdf5_add_2D_dataset_int8_t, \
                                             uint8_t: tld_hdf5_add_0D_dataset_uint8_t, \
                                             uint8_t*: tld_hdf5_add_1D_dataset_uint8_t, \
                                             uint8_t**: tld_hdf5_add_2D_dataset_uint8_t, \
                                             int16_t: tld_hdf5_add_0D_dataset_int16_t, \
                                             int16_t*: tld_hdf5_add_1D_dataset_int16_t, \
                                             int16_t**: tld_hdf5_add_2D_dataset_int16_t, \
                                             uint16_t: tld_hdf5_add_0D_dataset_uint16_t, \
                                             uint16_t*: tld_hdf5_add_1D_dataset_uint16_t, \
                                             uint16_t**: tld_hdf5_add_2D_dataset_uint16_t, \
                                             int32_t: tld_hdf5_add_0D_dataset_int32_t, \
                                             int32_t*: tld_hdf5_add_1D_dataset_int32_t, \
                                             int32_t**: tld_hdf5_add_2D_dataset_int32_t, \
                                             uint32_t: tld_hdf5_add_0D_dataset_uint32_t, \
                                             uint32_t*: tld_hdf5_add_1D_dataset_uint32_t, \
                                             uint32_t**: tld_hdf5_add_2D_dataset_uint32_t, \
                                             int64_t: tld_hdf5_add_0D_dataset_int64_t, \
                                             int64_t*: tld_hdf5_add_1D_dataset_int64_t, \
                                             int64_t**: tld_hdf5_add_2D_dataset_int64_t, \
                                             uint64_t: tld_hdf5_add_0D_dataset_uint64_t, \
                                             uint64_t*: tld_hdf5_add_1D_dataset_uint64_t, \
                                             uint64_t**: tld_hdf5_add_2D_dataset_uint64_t, \
                                             float:   tld_hdf5_add_0D_dataset_float, \
                                             float*:   tld_hdf5_add_1D_dataset_float, \
                                             float**:   tld_hdf5_add_2D_dataset_float, \
                                             double:  tld_hdf5_add_0D_dataset_double, \
                                             double*:  tld_hdf5_add_1D_dataset_double, \
                                             double**:  tld_hdf5_add_2D_dataset_double \
                )(F,G,N,V)


#define READ_ARRAY(type)                                              \
        EXTERN int tld_hdf5_read_0D_dataset_ ##type (struct hdf5_data* hdf5_data, char* group, char* name, type* data); \
        EXTERN int tld_hdf5_read_1D_dataset_ ##type (struct hdf5_data* hdf5_data, char* group, char* name, type** data); \
        EXTERN int tld_hdf5_read_2D_dataset_ ##type (struct hdf5_data* hdf5_data, char* group, char* name, type*** data);


READ_ARRAY(char)
READ_ARRAY(int8_t)
READ_ARRAY(uint8_t)
READ_ARRAY(int16_t)
READ_ARRAY(uint16_t)
READ_ARRAY(int32_t)
READ_ARRAY(uint32_t)
READ_ARRAY(int64_t)
READ_ARRAY(uint64_t)
READ_ARRAY(float)
READ_ARRAY(double)


#undef READ_ARRAY


#define HDF_READ_DATA(F,G,N,V) _Generic((V),                        \
                                            char*: tld_hdf5_read_0D_dataset_char, \
                                            char**: tld_hdf5_read_1D_dataset_char, \
                                            char***: tld_hdf5_read_2D_dataset_char, \
                                            int8_t*: tld_hdf5_read_0D_dataset_int8_t, \
                                            int8_t**: tld_hdf5_read_1D_dataset_int8_t, \
                                            int8_t***: tld_hdf5_read_2D_dataset_int8_t, \
                                            uint8_t*: tld_hdf5_read_0D_dataset_uint8_t, \
                                            uint8_t**: tld_hdf5_read_1D_dataset_uint8_t, \
                                            uint8_t***: tld_hdf5_read_2D_dataset_uint8_t, \
                                            int16_t*: tld_hdf5_read_0D_dataset_int16_t, \
                                            int16_t**: tld_hdf5_read_1D_dataset_int16_t, \
                                            int16_t***: tld_hdf5_read_2D_dataset_int16_t, \
                                            uint16_t*: tld_hdf5_read_0D_dataset_uint16_t, \
                                            uint16_t**: tld_hdf5_read_1D_dataset_uint16_t, \
                                            uint16_t***: tld_hdf5_read_2D_dataset_uint16_t, \
                                            int32_t*: tld_hdf5_read_0D_dataset_int32_t, \
                                            int32_t**: tld_hdf5_read_1D_dataset_int32_t, \
                                            int32_t***: tld_hdf5_read_2D_dataset_int32_t, \
                                            uint32_t*: tld_hdf5_read_0D_dataset_uint32_t, \
                                            uint32_t**: tld_hdf5_read_1D_dataset_uint32_t, \
                                            uint32_t***: tld_hdf5_read_2D_dataset_uint32_t, \
                                            int64_t*: tld_hdf5_read_0D_dataset_int64_t, \
                                            int64_t**: tld_hdf5_read_1D_dataset_int64_t, \
                                            int64_t***: tld_hdf5_read_2D_dataset_int64_t, \
                                            uint64_t*: tld_hdf5_read_0D_dataset_uint64_t, \
                                            uint64_t**: tld_hdf5_read_1D_dataset_uint64_t, \
                                            uint64_t***: tld_hdf5_read_2D_dataset_uint64_t, \
                                            float*:   tld_hdf5_read_0D_dataset_float, \
                                            float**:   tld_hdf5_read_1D_dataset_float, \
                                            float***:   tld_hdf5_read_2D_dataset_float, \
                                            double*:  tld_hdf5_read_0D_dataset_double, \
                                            double**:  tld_hdf5_read_1D_dataset_double, \
                                            double***:  tld_hdf5_read_2D_dataset_double \
                )(F,G,N,V)


#define ADD_ATTR(type)                                                  \
        EXTERN int tld_hdf5_add_attribute_ ##type(struct hdf5_data* hdf5_data, char* group, char* name,type x);

ADD_ATTR(int8_t)
ADD_ATTR(uint8_t)
ADD_ATTR(int16_t)
ADD_ATTR(uint16_t)
ADD_ATTR(int32_t)
ADD_ATTR(uint32_t)
ADD_ATTR(int64_t)
ADD_ATTR(uint64_t)
ADD_ATTR(float)
ADD_ATTR(double)

#undef ADD_ATTR

EXTERN int tld_hdf5_add_attribute_string(struct hdf5_data* hdf5_data,char* group, char* name,char* x);

#define HDF_WRITE_ATTRIBUTE(F,G,N,V) _Generic((V),      \
                int8_t: tld_hdf5_add_attribute_int8_t,      \
                uint8_t: tld_hdf5_add_attribute_uint8_t,    \
                int16_t: tld_hdf5_add_attribute_int16_t,    \
                uint16_t: tld_hdf5_add_attribute_uint16_t,  \
                int32_t: tld_hdf5_add_attribute_int32_t,    \
                uint32_t: tld_hdf5_add_attribute_uint32_t,  \
                int64_t: tld_hdf5_add_attribute_int64_t,    \
                uint64_t: tld_hdf5_add_attribute_uint64_t,  \
                float: tld_hdf5_add_attribute_float,        \
                double: tld_hdf5_add_attribute_double,      \
                char*: tld_hdf5_add_attribute_string        \
                )(F,G,N,V)


#define READ_ATTR(type)                                                  \
        EXTERN int tld_hdf5_read_attribute_ ##type(struct hdf5_data* hdf5_data, char* group, char* name,type* x);


READ_ATTR(int8_t)
READ_ATTR(uint8_t)
READ_ATTR(int16_t)
READ_ATTR(uint16_t)
READ_ATTR(int32_t)
READ_ATTR(uint32_t)
READ_ATTR(int64_t)
READ_ATTR(uint64_t)
READ_ATTR(float)
READ_ATTR(double)

#undef READ_ATTR


EXTERN int tld_hdf5_read_attribute_string(struct hdf5_data* hdf5_data, char* group,char* name, char** x);

#define HDF_READ_ATTRIBUTE(F,G,N,V) _Generic((V),                     \
                int8_t*: tld_hdf5_read_attribute_int8_t,                  \
                uint8_t*: tld_hdf5_read_attribute_uint8_t,    \
                int16_t*: tld_hdf5_read_attribute_int16_t,    \
                uint16_t*: tld_hdf5_read_attribute_uint16_t,  \
                int32_t*: tld_hdf5_read_attribute_int32_t,    \
                uint32_t*: tld_hdf5_read_attribute_uint32_t,  \
                int64_t*: tld_hdf5_read_attribute_int64_t,    \
                uint64_t*: tld_hdf5_read_attribute_uint64_t,  \
                float*: tld_hdf5_read_attribute_float,        \
                double*: tld_hdf5_read_attribute_double,      \
                char**: tld_hdf5_read_attribute_string        \
                )(F,G,N,V)

EXTERN int tld_hdf5_open_group(struct hdf5_data* hdf5_data, char* groupname);
EXTERN int tld_hdf5_close_group(struct hdf5_data* hdf5_data);


#undef TLHDF5_IMPORT
#undef EXTERN

#endif
