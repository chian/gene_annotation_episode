#include "tld.h"
#include <stdio.h>

int rng_dist_test(void);
static void printHistogram(double* values, int n);

int main(void)
{
        struct rng_state* rng = NULL;
        double* values = NULL;
        double mean = 0.0;
        double stdev = 1.0;

        int num_val = 1000000;
        int i,j;

        RUN(init_rng(&rng,0));

        MMALLOC(values,sizeof(double) * num_val);

        LOG_MSG("Gaussian");
        for(i = 0; i < num_val;i++){
                values[i] = tl_random_gaussian(rng,mean,stdev);
                //fprintf(stdout,"%f\t%d\n", tl_random_double(rng_second), tl_random_int(rng_second,10));
        }

        printHistogram(values,num_val);
        LOG_MSG("Gamma");

        for(i = 0; i < 100;i+=5){
                mean = 0.0;
                for(j = 0; j < 10;j++){
                        values[j] = tl_random_gamma(rng, (double) i + 0.01,1.0);
                        mean+=values[j];
                }
                for(j = 0; j < 10;j++){
                        values[j] /= mean;
                }
                for(j = 0; j < 10;j++){
                        fprintf(stdout,"%0.2f ",values[j]);
                }
                fprintf(stdout,"\n");
        }

        MFREE(values);



        LOG_MSG("Double");
        for(int i = 0; i < 10;i++){
                double r = tl_random_double( rng);
                LOG_MSG("%d %f",i, r);
        }
        free_rng(rng);

        LOG_MSG("Test rngdist");
        RUN(rng_dist_test());
        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;
}


int rng_dist_test(void)
{
        double* w = NULL;
        int* out = NULL;
        struct rng_dist* d = NULL;
        double sum;
        galloc(&w, 6);
        galloc(&out,6);
        for(int i = 0; i < 6;i++){
                w[i] = 1.0;
                out[i] = 0;
        }
        w[2] = 2.0;

        sum = 0.0;
        for(int i = 0; i < 6;i++){
                sum += w[i];
        }
        RUN(tl_random_sdist_init(&d, w, 6, 0));
        for(int i = 0; i < 10000000;i++){
                out[tl_random_sdist_smpl(d)]++;
        }

        for(int i = 0; i < 6;i++){
                fprintf(stdout,"%3d\t%f\t%f\n",i,(double) out[i] /  10000000.0,w[i]/sum);
        }
        tl_random_sdist_free(d);
        gfree(w);
        gfree(out);
        return OK;
ERROR:
        gfree(w);
        gfree(out);
        return FAIL;
}


/* from RosettaCode */
// https://rosettacode.org/wiki/Statistics/Normal_distribution#C

void printHistogram(double* values, int n)
{
        const int width = 50;
        int max = 0;

        const double low   = -3.05;
        const double high  =  3.05;
        const double delta =  0.1;

        int i,j,k;
        int nbins = (int)((high - low) / delta);
        int* bins = (int*)calloc(nbins,sizeof(int));
        if ( bins != NULL )
        {
                for ( i = 0; i < n; i++ )
                {
                        int j = (int)( (values[i] - low) / delta );
                        if ( 0 <= j  &&  j < nbins )
                                bins[j]++;
                }

                for ( j = 0; j < nbins; j++ )
                        if ( max < bins[j] )
                                max = bins[j];

                for ( j = 0; j < nbins; j++ )
                {
                        printf("(%5.2f, %5.2f) |", low + j * delta, low + (j + 1) * delta );
                        k = (int)( (double)width * (double)bins[j] / (double)max );
                        while(k-- > 0) putchar('*');
                        printf("  %-.1f%%", bins[j] * 100.0 / (double)n);
                        putchar('\n');
                }

                free(bins);
        }
}
