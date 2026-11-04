#include "tld.h"
#include <stdio.h>

int rng_dist_test(void);

int main(void)
{
        #ifdef DEBUG
        LOG_MSG("DEBUG");
        #endif
        LOG_MSG("All good!");
        WARNING_MSG("WARNING");
        if(1 == 0){
                ERROR_MSG("no longer");
        }

        int* f = NULL;
        double* d = NULL;

        galloc(&f, 19);
        galloc(&f, 1186718291);
        LOG_MSG("Pointer in maon: %p", f);
        for(int i = 0; i < 19;i++){
                f[i] = i;
        }
        galloc(&d, 1900);
        gfree(f);
        gfree(d);


        LOG_MSG("About to move to 2D");
        float** mat = NULL;
        int dim1;
        int dim2;
        dim1 = 24;
        dim2 = 15;

        galloc(&mat, dim1,dim2);

        for(int i = 0; i < dim1; i++){
                for(int j = 0; j < dim2;j++){
                        mat[i][j] = MACRO_MAX(i,j);
                        fprintf(stdout,"%0.1f ", mat[i][j]);
                }
                fprintf(stdout,"\n");
        }
        fprintf(stdout,"\n");


        gfree(mat);

        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;
}
