#include "tld.h"
#include <stdio.h>


int main(void)
{
        struct rng_state* rng = NULL;
        int len = 15;
        double* d_arr = NULL;
        uint8_t* small_arr = NULL;
        RUN(init_rng(&rng, 42));

        galloc(&d_arr,len);
        galloc(&small_arr,len);
        for(int i = 0;i < len;i++){
                d_arr[i] = tl_random_double(rng)*10.0;
        }

        for(int i = 0;i < 10;i++){
                fprintf(stdout,"ORG    : ");
                for(int j = 0; j < len;j++){
                        fprintf(stdout,"%f ", d_arr[j]);
                }
                fprintf(stdout,"\n");

                TLD_SHUFFLE(d_arr,len, rng);
                fprintf(stdout,"SHUFFLE: ");
                for(int j = 0; j < len;j++){
                        fprintf(stdout,"%f ", d_arr[j]);
                }
                fprintf(stdout,"\n");
        }
        
        gfree(d_arr);
        gfree(small_arr);

        free_rng(rng);
        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;
}
