#ifndef TLD_CORE_H
#define TLD_CORE_H

/* these headers are used by all bits of the library */
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

#ifndef tld_external
#ifdef __cplusplus
#define tld_external extern "C"
#else
#define tld_external extern
#endif
#endif

#ifndef tld_internal
#define tld_internal static
#endif

/* Define generally useful macros  */

#define tld_stringify(x) #x
#define tld_tostring(x) tld_stringify(x)


#define OK              0
#define FAIL            1

/* Need to revisit  */
#define MACRO_MIN(a,b)          (((a)<(b))?(a):(b))
#define MACRO_MAX(a,b)          (((a)>(b))?(a):(b))



#define ASSERT(TEST,...)  if(!(TEST)) {                         \
                tld_message(MESSAGE_TYPE_ERROR, #TEST );        \
                tld_message(MESSAGE_TYPE_ERROR, __VA_ARGS__ );  \
                goto ERROR;                                     \
        }

/* Messages  */
#define MESSAGE_TYPE_MSG 0
#define MESSAGE_TYPE_WARNING 1
#define MESSAGE_TYPE_ERROR 2
#define LOG_MSG(...) (tld_message(MESSAGE_TYPE_MSG, __VA_ARGS__ ))
#define WARNING_MSG(...) (tld_message(MESSAGE_TYPE_WARNING, __VA_ARGS__ ))
#define ERROR_MSG(...) do {                                     \
                tld_message(MESSAGE_TYPE_ERROR, __VA_ARGS__ );  \
                goto ERROR;                                     \
        }while (0)


/* Checking for function return  */
#define ADDFAILED(x)  "Function \"" tld_tostring(x) "\" failed."
#define RUN(EXP)                                \
        if((EXP) != OK){                        \
                tld_message(MESSAGE_TYPE_ERROR,ADDFAILED(EXP)); \
                goto ERROR;                                     \
        }



tld_external void tld_message(uint8_t type, const char *format, ...);

#endif
