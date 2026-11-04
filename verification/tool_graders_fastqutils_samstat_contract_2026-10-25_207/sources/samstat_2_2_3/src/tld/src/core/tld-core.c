#include "tld-core.h"

#include <stdio.h>
#include <time.h>

#define TYPE_MARGIN 8
#define MESSAGE_MARGIN 22


#define AT __FILE__ " line " tld_tostring(__LINE__)

/* #define AT __FILE__ " line " tld_tostring(__LINE__) */

tld_internal void vlog(uint8_t type,FILE* f_ptr,const char *format,  va_list argp);
tld_internal void verror(FILE* f_ptr, const char *format,  va_list argp);

tld_internal int get_time(char* time_ptr, int size);

void tld_message(uint8_t type, const char *format, ...)
{
        va_list argp = {0};
        va_start(argp, format);
        vlog(type,stdout,format, argp);
        va_end(argp);
}

void error(const char *format, ...)
{
        va_list argp = {0};
        va_start(argp, format);
        verror(stderr,format,argp);
        va_end(argp);
}

void vlog( uint8_t type, FILE* f_ptr,const char *format,  va_list argp)
{
        char time_string[BUFSIZ];

        if(get_time(time_string,BUFSIZ) != OK){
                fprintf(stderr,"notime");
        }
        fprintf(f_ptr,"%*s: ",MESSAGE_MARGIN,time_string);
        switch (type) {
        case MESSAGE_TYPE_MSG: {
                fprintf(f_ptr,"%*s: ",TYPE_MARGIN,"LOG ");
                vfprintf(f_ptr, format, argp);
                fprintf(f_ptr,"\n");
                break;
        }
        case MESSAGE_TYPE_WARNING: {
                fprintf(f_ptr,"%*s: ",TYPE_MARGIN,"WARNING ");
                vfprintf(f_ptr, format, argp);
                fprintf(f_ptr,"\n");
                break;
        }
        case MESSAGE_TYPE_ERROR: {
                fprintf(f_ptr,"%*s: ",TYPE_MARGIN,"ERROR ");
                vfprintf(f_ptr, format, argp);
                fprintf(f_ptr," (%s)\n",AT);
                break;
        }
        default:
                fprintf(f_ptr,"Unrecognized Message type (in tld) - this should never happen");
                break;
        }

        fflush(f_ptr);
}

void verror(FILE* f_ptr, const char *format,  va_list argp)
{
        char time_string[BUFSIZ];
        if(get_time(time_string, BUFSIZ) != OK){
                fprintf(stderr,"notime");
        }
        fprintf(f_ptr,"%*s: ",MESSAGE_MARGIN,time_string);
        fprintf(f_ptr,"%*s: ",TYPE_MARGIN,"ERROR ");
        vfprintf(f_ptr, format, argp);
        fprintf(f_ptr," (%s)\n",AT);
        fflush(f_ptr);
}


int get_time(char* time_ptr, int size)
{
        /* time_t timer = 0; */
        /* struct tm* tm_info = NULL; */

        /* timer = time(NULL); */
        /* localtime_r(&timer, tm_info); */

        struct tm newtime;
        time_t ltime = 0;
        /* char buf[50]; */

        ltime=time(&ltime);
        localtime_r(&ltime, &newtime);


        if(!strftime(time_ptr, size, "[%F %H:%M:%S] ", &newtime)){
                /* ERROR_MSG("write failed"); */
                fprintf(stderr,"%*s: ",TYPE_MARGIN,"ERROR ");
                fprintf(stderr, "Could not get the time");
                fprintf(stderr," (%s)\n",AT);
                goto ERROR;
        }
        return OK;
ERROR:
        return FAIL;
}
