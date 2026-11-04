#include <sys/time.h>
#include "stdio.h"

static int timeval_subtract(struct timeval *result, struct timeval end, struct timeval start);

int timeval_subtract(struct timeval *result, struct timeval end, struct timeval start)
{
        if (start.tv_usec < end.tv_usec) {
                int nsec = (end.tv_usec - start.tv_usec) / 1000000 + 1;
                end.tv_usec -= 1000000 * nsec;
                end.tv_sec += nsec;
        }
        if (start.tv_usec - end.tv_usec > 1000000) {
                int nsec = (end.tv_usec - start.tv_usec) / 1000000;
                end.tv_usec += 1000000 * nsec;
                end.tv_sec -= nsec;
        }

        result->tv_sec = end.tv_sec - start.tv_sec;
        result->tv_usec = end.tv_usec - start.tv_usec;

        return end.tv_sec < start.tv_sec;
}

void set_exec_time(int end)
{
        static struct timeval time_start;
        struct timeval time_end;
        struct timeval time_diff;

        if (end) {
                gettimeofday(&time_end, NULL);
                if (timeval_subtract(&time_diff, time_end, time_start) == 0) {
                        if (end == 1)
                                fprintf(stdout,"\nexec time: %1.2fs\n",time_diff.tv_sec + (time_diff.tv_usec / 1000000.0f));
                        else if (end == 2)
                                fprintf(stdout,"%1.2fs",time_diff.tv_sec + (time_diff.tv_usec / 1000000.0f));
                }
                return;
        }
        gettimeofday(&time_start, NULL);
}
