#include "../core/tld-core.h"
#include "../alloc/tld-alloc.h"
#include "basic.h"
#include <math.h>
#include <float.h>
#include <stdint.h>
/*
  adopted from:

  https://metacpan.org/release/JANERT/Statistics-KernelEstimation-0.05/source/lib/Statistics/KernelEstimation.pm
*/
static int copy_steps(double *data, int data_len, double ***ret);
static int create_steps(double *data, int data_len, int n_steps, double*** ret);
static int default_bandwidth(double *x,double* cnt, int len, double* band);


int tld_kde_pdf(double *data, int data_len, int n_steps, double ***out)
{
        double total_cnt = 0.0;
        double band = 0.1;

        double** ladder = NULL;
        uint8_t n_data = 0;

        /* * ASSERT(data == NULL & cnt == NULL,"No data to work with!"); *\/ */
        ASSERT(data_len > 0,"No data len?");


        create_steps(data,data_len, n_steps, &ladder);

        RUN(default_bandwidth(data,NULL,data_len,&band));

        /* LOG_MSG("BAND: %f", band); */

        total_cnt = data_len;

        /* LOG_MSG("bandwidth: %f",band); */
        for(int i = 0; i < n_steps;i++){
                double d = 0.0;

                for(int j = 0; j < data_len; j++){
                        double add_d = 0.0;
                        tld_normal_pdf(ladder[i][0], data[j], band,&add_d);
                        d+= add_d;
                }
                d  = d / total_cnt;
                ladder[i][1] = d;
        }
        /* LOG_MSG("%f %f", test,d); */

        if(n_data){
                gfree(data);
        }
        *out = ladder;
        /* gfree(ladder); */

        return OK;
ERROR:
        if(n_data){
                gfree(data);
        }
        return FAIL;
}

int tld_kde_count_pdf(double *data,double* cnt, int data_len, double*** out)
{
        double total_cnt = 0.0;
        double band = 0.1;

        double** ladder = NULL;
        uint8_t n_data = 0;

        /* * ASSERT(data == NULL & cnt == NULL,"No data to work with!"); *\/ */
        ASSERT(data_len > 0,"No data len?");


        RUN(copy_steps(data,data_len, &ladder ));


        RUN(default_bandwidth(data,cnt,data_len,&band));

        /* LOG_MSG("BAND: %f", band); */

        total_cnt = 0.0;
        for(int i = 0; i < data_len; i++){
                total_cnt += cnt[i];
        }

        /* LOG_MSG("bandwidth: %f",band); */
        for(int i = 0; i < data_len;i++){
                double d = 0.0;

                for(int j = 0; j < data_len; j++){
                        double add_d = 0.0;
                        tld_normal_pdf(ladder[i][0], data[j], band,&add_d);
                        add_d = add_d * cnt[j];
                        d+= add_d;
                }
                d  = d / total_cnt;
                ladder[i][1] = d;
        }
        /* LOG_MSG("%f %f", test,d); */

        if(n_data){
                gfree(data);
        }
        *out = ladder;
        /* gfree(ladder); */

        return OK;
ERROR:
        if(n_data){
                gfree(data);
        }
        return FAIL;
}

int copy_steps(double *data, int data_len, double ***ret)
{
        double** x = NULL;
        galloc(&x, data_len,2);

        for(int i = 0; i < data_len;i++){
                x[i][0] = data[i];
                /* LOG_MSG("%d %f",i, x[i][0]); */
                x[i][1] = 0.0;
        }
        *ret = x;
        return OK;
ERROR:
        if(x){
                gfree(x);
        }
        return FAIL;
}

int create_steps(double *data, int data_len, int n_steps, double*** ret)
{
        double** x = NULL;
        double min = DBL_MAX;
        double max = -DBL_MAX;
        double step = 0.0;
        for(int i = 0;i < data_len;i++){
                if(max < data[i]){
                        max = data[i];
                }
                if(min > data[i]){
                        min = data[i];
                }
        }
        step = (max- min)  / (double)(n_steps);
        /* LOG_MSG("Min : %f",min); */
        /* LOG_MSG("Max : %f",max); */
        galloc(&x, n_steps,2);
        
        for(int i = 0; i < (int) n_steps;i++){
                x[i][0] = min + (double) i * step + step / 2.0;
                /* LOG_MSG("%d %f",i, x[i][0]); */
                x[i][1] = 0.0;
        }
        *ret = x;
        return OK;
ERROR:
        gfree(x);
        return FAIL;

}

int default_bandwidth(double *x,double* cnt, int len, double* band)
{
        double sum_x = 0.0;
        double sum_xx = 0.0;
        double a;
        double a2;
        double sigma;
        double sum = 0.0;
        for(int i = 0; i < len; i++){
                if(cnt){
                        sum_x += cnt[i] * x[i];
                        sum_xx += cnt[i] * x[i] * x[i];
                        sum += cnt[i];
                }else{
                        sum_x += x[i];
                        sum_xx += x[i] * x[i];
                        sum = sum + 1.0;
                }

        }

        a = sum_x / sum;
        a2 = sum_xx / sum;

        sigma = sqrt(a2 - pow(a, 2.0));

        *band = sigma * pow(3.0 * sum / 4.0 , -1.0 / 5.0 );
        return OK;
}
