#include "rng/tld-rng.h"
#include "tld.h"
#include <math.h>


int main(void)
{
        struct rng_state* rng = NULL;
        double* vec = NULL;
        double* noise = NULL;
        double var = 0.0;
        double mu = 0.0;
        int n = 1000;

        RUN(init_rng(&rng, 0));

        galloc(&vec,n);
        galloc(&noise,n);

        for(int i = 0; i < n;i++){
                vec[i] = tl_random_double(rng)+10.0;
        }

        tld_sample_variance(vec, n, &var);
        LOG_MSG("Variance of original data: %f", var);

        mu = sqrt(var*0.5);
        /* mu = mu *0.5; */
        for(int i = 0; i < n;i++){
                noise[i] = tl_random_gaussian(rng, 0.0 , mu);
        }
        tld_sample_variance(noise, n, &var);

        LOG_MSG("Variance of    noise data: %f", var);

        mu = sqrt(var);
        /* mu = mu *0.5; */
        for(int i = 0; i < n;i++){
                noise[i] = tl_random_gaussian(rng, 0.0 ,0.5 *  mu);
        }
        tld_sample_variance(noise, n, &var);

        LOG_MSG("Variance of    noise data: %f", var);

        gfree(noise);
        gfree(vec);
        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;

}
