#include "tld.h"
#include <stdio.h>

int main(void)
{
        double y = 0.0;

        struct rng_state* rng = NULL;

        RUN(init_rng(&rng, 0));

        for(int i = 0; i < 10000;i++){
                double x = tl_random_double(rng)* 2000000.0  - 1000000.0;
                tld_sigmoid(x, &y);
                LOG_MSG("%d %f %f", i, y, x);
        }

        free(rng);
        return EXIT_SUCCESS;
ERROR:
        if(rng){
                free_rng(rng);
        }
        return EXIT_FAILURE;
}
