#include "../core/tld-core.h"
#include <math.h>
#define BASIC_IMPORT
#include "basic.h"

int tld_shannon(double *vec, int n, double *entropy)
{
        double t = 0.0;
        double s = 0.0;
        for(int i = 0; i < n;i++){
                t += vec[i];
        }
        for(int i = 0; i < n;i++){
                if(vec[i]){
                        double p = vec[i] / t;
                        s += p * log2(p);
                }
        }

        s = s * -1.0;
        *entropy = s;
        return OK;
}

int tld_mean(double *vec, int n, double *mean)
{
        ASSERT(vec != NULL, "No vector");
        double m = 0.0;
        for(int i = 0; i < n;i++){
                m += vec[i];
        }
        m /= (double) n;
        /* LOG_MSG("Mean: %f",m); */
        *mean = m;
        return OK;
ERROR:
        return FAIL;
}

int tld_pop_variance(double *vec, int n, double *variance)
{
        ASSERT(vec != NULL, "No vector");
        double m = 0.0;
        double v = 0.0;
        RUN(tld_mean(vec, n, &m));
        v = 0.0;
        for(int i = 0; i < n;i++){
                v += pow(vec[i] - m, 2.0);
        }
        v /= (double) n;
        *variance = v;
        return OK;
ERROR:
        return FAIL;
}

int tld_sample_variance(double *vec, int n, double *variance)
{
        ASSERT(vec != NULL, "No vector");
        double m = 0.0;
        double v = 0.0;
        RUN(tld_mean(vec, n, &m));
        v = 0.0;
        for(int i = 0; i < n;i++){
                v += pow(vec[i] - m, 2.0);
        }
        v /= (double) (n-1);
        *variance = v;
        return OK;
ERROR:
        return FAIL;
}


int tld_normal_pdf(double x, double mu, double sigma, double* p)
{
        double z;
        ASSERT(sigma != 0.0, "stdev is 0.")
        z = (x - mu) / sigma;

        *p = exp(-z*z*0.5) / (sigma * sqrt(2. * 3.14159265358979323846264338328));

        return OK;
ERROR:
        return FAIL;
}

int tld_sigmoid(double x, double *out)
{
        double y;

        ASSERT(isinf(x) == 0, "x is infinite");
        ASSERT(isnan(x) == 0, "x is Nan");
        if(x < 0.0){
                y = exp(x);
                y = y / (1.0 + y);
        }else{
                y = 1.0 / (1.0 + exp(-1.0 * x));
        }
        *out = y;
        return OK;
ERROR:
        return FAIL;
}
