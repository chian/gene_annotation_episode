#include "tld.h"

int main(void)
{
        double* vec = NULL;
        double var = 0.0;
        galloc(&vec,10);

        for(int i = 0; i < 10;i++){
                vec[i] = (double) (i+1) ;
        }

        tld_sample_variance(vec, 10, &var);
        for(int i = 0; i < 10;i++){
                LOG_MSG("%d %f",i, vec[i]);
        }
        LOG_MSG("Var: %f", var);
        gfree(vec);
        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;

}
