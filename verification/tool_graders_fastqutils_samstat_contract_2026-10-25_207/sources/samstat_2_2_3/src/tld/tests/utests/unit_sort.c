#include "tld.h"
#include <stdio.h>

int main(void)
{
        struct rng_state* rng = NULL;
        RUN(init_rng(&rng,0));

        float* x_flt = NULL;
        galloc(&x_flt, 10);

        for(int i = 0; i < 10;i++){
                x_flt[i] = (float) tl_random_double(rng);
        }

        TLD_SORT_DESC(x_flt,10);
        for(int i = 0; i < 10;i++){
                fprintf(stdout,"%f ", x_flt[i]);
        }
        fprintf(stdout,"\n");

        TLD_SORT_ASC(x_flt,10);
        for(int i = 0; i < 10;i++){
                fprintf(stdout,"%f ", x_flt[i]);
        }
        fprintf(stdout,"\n");

        gfree(x_flt);

        char* x_char = NULL;
        galloc(&x_char, 10);

        for(int i = 0; i < 10;i++){
                x_char[i] = (char) tl_random_int(rng, 26) + 65;
        }

        TLD_SORT_DESC(x_char,10);
        for(int i = 0; i < 10;i++){
                fprintf(stdout,"%c", x_char[i]);
        }
        fprintf(stdout,"\n");

        TLD_SORT_ASC(x_char,10);
        for(int i = 0; i < 10;i++){
                fprintf(stdout,"%c", x_char[i]);
        }
        fprintf(stdout,"\n");

        gfree(x_char);


        free_rng(rng);

        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;
}
