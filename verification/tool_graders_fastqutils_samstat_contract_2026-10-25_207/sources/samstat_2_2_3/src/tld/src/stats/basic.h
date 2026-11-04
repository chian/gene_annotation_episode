#ifndef BASIC_H
#define BASIC_H

#ifdef BASIC_IMPORT
#define EXTERN
#else
#define EXTERN extern
#endif

EXTERN int tld_shannon(double *vec, int n, double *entropy);

EXTERN int tld_mean(double *vec, int n, double *mean);
EXTERN int tld_pop_variance(double *vec, int n, double *variance);
EXTERN int tld_sample_variance(double *vec, int n, double *variance);


EXTERN int tld_sigmoid(double x, double *out);

EXTERN int tld_normal_pdf(double x, double mu, double sigma, double* p);


EXTERN int tld_kde_pdf(double *data, int data_len, int n_steps, double ***out);
EXTERN int tld_kde_count_pdf(double *data,double* cnt, int data_len, double*** out);
#undef BASIC_IMPORT
#undef EXTERN


#endif
