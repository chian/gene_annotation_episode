#include "tld.h"
#include <stdio.h>


int main(void)
{
        TLD_START_TIMER;

        double x = 0.0;

        for(int i = 0; i < 10000000;i++){
                x+= (double) i + sqrt((double) i );
        }
        LOG_MSG("Sleeping");
        /* sleep(10); */
        LOG_MSG("%f", x);

        TLD_END_TIMER;

        return EXIT_SUCCESS;
}
