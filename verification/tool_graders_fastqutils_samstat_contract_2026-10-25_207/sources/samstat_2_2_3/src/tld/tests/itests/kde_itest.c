#include "tld.h"

int main(void)
{
        struct rng_state* rng = NULL;
        double* x = NULL;
        double r = 0.0;
        int len = 10000;

        RUN(init_rng(&rng,0));
        galloc(&x, len);

        for(int i = 0;i < len;i++){
                r = tl_random_double(rng);
                if(r < 0.3){
                        x[i] = tl_random_gaussian(rng, 1.0, 0.2);
                }else{
                        x[i] = tl_random_gaussian(rng, 5.0, 1.0);
                }

        }

        /* FILE* f_ptr = NULL; */


        /* f_ptr = fopen("kde_dat.csv","w"); */
        /* for(int i = 0;i < len;i++){ */
        /*         fprintf(f_ptr,"%f\n",x[i]); */
        /* } */

        /* fclose(f_ptr); */
        double** ladder = NULL;
        tld_kde_pdf(x, len, 20, &ladder);

        for(int i = 0; i < 20;i++){
                fprintf(stdout,"%d %f,%f\n",i, ladder[i][0],ladder[i][1]);
        }

        gfree(ladder);



        gfree(x);

        x = NULL;

        double* y = NULL;
        len = 10;
        galloc(&x,len);
        galloc(&y,len);
        for(int i = 0;i < len;i++){
                x[i] = i;
                y[i] = 0.0;
        }


        for(int i = 0;i < 10000;i++){
                r = tl_random_double(rng);
                int a = 0;
                if(r < 0.3){
                        a = (int) round(tl_random_gaussian(rng, 1.0, 0.2));

                }else{
                        a = (int) round(tl_random_gaussian(rng, 5.0, 1.0));
                }
                /* LOG_MSG("a = %d", a); */
                a = MACRO_MAX(0, a);
                a = MACRO_MIN(9, a);

                y[a]++;
        }

        /* for(int i = 0;i < len;i++){ */
        /*         fprintf(stdout,"%d %f %f\n",i , x[i], y[i]); */
        /* } */
        ladder = NULL;
        tld_kde_count_pdf(x,y,len ,&ladder);




        for(int i = 0; i < len;i++){
                fprintf(stdout,"%f %f -> %f,%f\n",x[i],y[i], ladder[i][0],ladder[i][1]);
        }


        gfree(ladder);

        if(x){
                gfree(x);
        }
        if(y){
                gfree(y);
        }

        free_rng(rng);
        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;
}

