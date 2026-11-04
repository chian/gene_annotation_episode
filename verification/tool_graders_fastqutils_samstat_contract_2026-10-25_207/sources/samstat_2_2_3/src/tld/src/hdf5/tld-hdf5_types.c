#include "../core/tld-core.h"
#include <hdf5.h>

#include "tld-hdf5_types.h"


int set_type_char(hid_t* type)
{

        *type = H5Tcopy(H5T_STD_U8LE);//H5T_NATIVE_CHAR;
        return OK;
}

int set_type_int8_t(hid_t* type)
{
        *type = H5Tcopy(H5T_STD_I8LE);//H5T_NATIVE_INT8;
        return OK;
}

int set_type_uint8_t(hid_t* type)
{
        *type = H5Tcopy(H5T_STD_U8LE);//H5T_NATIVE_UINT8;
        return OK;
}

int set_type_int16_t(hid_t* type)
{
        *type = H5Tcopy(H5T_STD_I16LE);//H5T_NATIVE_INT16;
        return OK;
}

int set_type_uint16_t(hid_t* type)
{
        *type = H5Tcopy(H5T_STD_U16LE);//H5T_NATIVE_UINT16;
        return OK;
}

int set_type_int32_t(hid_t* type)
{
        *type = H5Tcopy(H5T_STD_I32LE);//H5T_NATIVE_INT32;
        return OK;
}

int set_type_uint32_t(hid_t* type)
{
        *type = H5Tcopy(H5T_STD_U32LE);//H5T_NATIVE_UINT32;
        return OK;
}
int set_type_int64_t(hid_t* type)
{
        *type = H5Tcopy(H5T_STD_I64LE);//H5T_NATIVE_INT64;
        return OK;
}

int set_type_uint64_t(hid_t* type)
{
        *type = H5Tcopy(H5T_STD_U64LE);//H5T_NATIVE_UINT64;
        return OK;
}

int set_type_float(hid_t* type)
{
        *type = H5Tcopy(H5T_IEEE_F32LE);//H5T_NATIVE_FLOAT;
        return OK;
}

int set_type_double(hid_t* type)
{
        *type = H5Tcopy(H5T_IEEE_F64LE);//H5T_NATIVE_DOUBLE;
        return OK;
}


int set_type_unknown(hid_t* type)
{

        WARNING_MSG("Could not determine type! (%d)",type);
        return FAIL;
}


void hdf5_print_type(hid_t type)
{
        switch (H5Tget_class(type)) {
        case H5T_INTEGER:
                if (H5Tequal(type, H5T_STD_I8BE))
                        LOG_MSG("H5T_STD_I8BE");
                else if (H5Tequal(type, H5T_STD_I8LE))
                        LOG_MSG("H5T_STD_I8LE");
                else if (H5Tequal(type, H5T_STD_I16BE))
                        LOG_MSG("H5T_STD_I16BE");
                else if (H5Tequal(type, H5T_STD_I16LE))
                        LOG_MSG("H5T_STD_I16LE");
                else if (H5Tequal(type, H5T_STD_I32BE))
                        LOG_MSG("H5T_STD_I32BE");
                else if (H5Tequal(type, H5T_STD_I32LE))
                        LOG_MSG("H5T_STD_I32LE");
                else if (H5Tequal(type, H5T_STD_I64BE))
                        LOG_MSG("H5T_STD_I64BE");
                else if (H5Tequal(type, H5T_STD_I64LE))
                        LOG_MSG("H5T_STD_I64LE");
                else if (H5Tequal(type, H5T_STD_U8BE))
                        LOG_MSG("H5T_STD_U8BE");
                else if (H5Tequal(type, H5T_STD_U8LE))
                        LOG_MSG("H5T_STD_U8LE");
                else if (H5Tequal(type, H5T_STD_U16BE))
                        LOG_MSG("H5T_STD_U16BE");
                else if (H5Tequal(type, H5T_STD_U16LE))
                        LOG_MSG("H5T_STD_U16LE");
                else if (H5Tequal(type, H5T_STD_U32BE))
                        LOG_MSG("H5T_STD_U32BE");
                else if (H5Tequal(type, H5T_STD_U32LE))
                        LOG_MSG("H5T_STD_U32LE");
                else if (H5Tequal(type, H5T_STD_U64BE))
                        LOG_MSG("H5T_STD_U64BE");
                else if (H5Tequal(type, H5T_STD_U64LE))
                        LOG_MSG("H5T_STD_U64LE");
                else if (H5Tequal(type, H5T_NATIVE_SCHAR))
                        LOG_MSG("H5T_NATIVE_SCHAR");
                else if (H5Tequal(type, H5T_NATIVE_UCHAR))
                        LOG_MSG("H5T_NATIVE_UCHAR");
                else if (H5Tequal(type, H5T_NATIVE_SHORT))
                        LOG_MSG("H5T_NATIVE_SHORT");
                else if (H5Tequal(type, H5T_NATIVE_USHORT))
                        LOG_MSG("H5T_NATIVE_USHORT");
                else if (H5Tequal(type, H5T_NATIVE_INT))
                        LOG_MSG("H5T_NATIVE_INT");
                else if (H5Tequal(type, H5T_NATIVE_UINT))
                        LOG_MSG("H5T_NATIVE_UINT");
                else if (H5Tequal(type, H5T_NATIVE_LONG))
                        LOG_MSG("H5T_NATIVE_LONG");
                else if (H5Tequal(type, H5T_NATIVE_ULONG))
                        LOG_MSG("H5T_NATIVE_ULONG");
                else if (H5Tequal(type, H5T_NATIVE_LLONG))
                        LOG_MSG("H5T_NATIVE_LLONG");
                else if (H5Tequal(type, H5T_NATIVE_ULLONG))
                        LOG_MSG("H5T_NATIVE_ULLONG");
                else
                        LOG_MSG("undefined integer");
                break;

        case H5T_FLOAT:
                if (H5Tequal(type, H5T_IEEE_F32BE))
                        LOG_MSG("H5T_IEEE_F32BE");
                else if (H5Tequal(type, H5T_IEEE_F32LE))
                        LOG_MSG("H5T_IEEE_F32LE");
                else if (H5Tequal(type, H5T_IEEE_F64BE))
                        LOG_MSG("H5T_IEEE_F64BE");
                else if (H5Tequal(type, H5T_IEEE_F64LE))
                        LOG_MSG("H5T_IEEE_F64LE");
                else if (H5Tequal(type, H5T_NATIVE_FLOAT))
                        LOG_MSG("H5T_NATIVE_FLOAT");
                else if (H5Tequal(type, H5T_NATIVE_DOUBLE))
                        LOG_MSG("H5T_NATIVE_DOUBLE");
                else if (H5Tequal(type, H5T_NATIVE_LDOUBLE))
                        LOG_MSG("H5T_NATIVE_LDOUBLE");
                else
                        LOG_MSG("undefined float");
                break;

        case H5T_BITFIELD:
                if (H5Tequal(type, H5T_STD_B8BE))
                        LOG_MSG("H5T_STD_B8BE");
                else if (H5Tequal(type, H5T_STD_B8LE))
                        LOG_MSG("H5T_STD_B8LE");
                else if (H5Tequal(type, H5T_STD_B16BE))
                        LOG_MSG("H5T_STD_B16BE");
                else if (H5Tequal(type, H5T_STD_B16LE))
                        LOG_MSG("H5T_STD_B16LE");
                else if (H5Tequal(type, H5T_STD_B32BE))
                        LOG_MSG("H5T_STD_B32BE");
                else if (H5Tequal(type, H5T_STD_B32LE))
                        LOG_MSG("H5T_STD_B32LE");
                else if (H5Tequal(type, H5T_STD_B64BE))
                        LOG_MSG("H5T_STD_B64BE");
                else if (H5Tequal(type, H5T_STD_B64LE))
                        LOG_MSG("H5T_STD_B64LE");
                else
                        LOG_MSG("undefined bitfield");
                break;

        case H5T_TIME:
        case H5T_STRING:
        case H5T_OPAQUE:
        case H5T_COMPOUND:
        case H5T_REFERENCE:
        case H5T_ENUM:
        case H5T_VLEN:
        case H5T_ARRAY:
        case H5T_NO_CLASS:
        case H5T_NCLASSES:
        default:
                return;

        } /* end switch */
}
