#include "../core/tld-core.h"
#include "hdf5.h"
#define TLDHDF5_UTILS_IMPORT
#include "tld-hdf5_utils.h"

#define STARTOF_DATA(type)                                      \
        int startof_galloc_ ##type(type x, void** ptr)          \
        {                                                       \
                *ptr = &x;                                      \
                return OK;                                      \
        }                                                       \
        int startof_galloc_ ##type ## _s(type* x, void** ptr)   \
        {                                                       \
                *ptr = &x[0];                                   \
                return OK;                                      \
        }                                                       \
        int startof_galloc_ ##type ## _ss(type** x, void** ptr) \
        {                                                       \
                *ptr = &x[0][0];                                \
                return OK;                                      \
        }

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
#undef STARTOF_DATA


int startof_galloc_unknown(void* x, void** ptr)
{
        ERROR_MSG("unknown data type: %p %p", x,*ptr);
        return OK;
ERROR:
        return FAIL;
}


