/* #include "hdf5/tld-hdf5wrap.h" */
/* #include "core/tld-core.h" */
/* #include "hdf5/tld-hdf5_struct.h" */
#include "core/tld-core.h"
#include "hdf5/tld-hdf5.h"
#include "tld.h"
#include <stdint.h>
#include <stdio.h>

#define FILENAME "test.h5"

int main(void)
{
        struct hdf5_data* f = NULL;
        char* hdf_path = NULL;
        double* d1d = NULL;
        double** d2d = NULL;
        uint64_t t = 10;
        galloc(&d1d,10);
        for(int i = 0; i < 10;i++){
                d1d[i] = (double)i;
        }

        galloc(&d2d,3,3);
        for(int i = 0; i < 3;i++){
                for(int j = 0; j < 3;j++){
                        d2d[i][j] = MACRO_MAX(i, j);
                }
        }

        tld_hdf5_open_file(&f, FILENAME);

        HDF_WRITE_DATA(f, "/dat1D","d1d",d1d);
        HDF_WRITE_DATA(f, "/dat2D","d2d",d2d);
        HDF_WRITE_DATA(f, "/dat0D","d1d",t);
        tld_hdf5_close_file(&f);

        LOG_MSG("Got here - close file");
        double* read_d1d = NULL;
        double** read_d2d = NULL;
        uint64_t read_t = 0;
        tld_hdf5_open_file(&f, FILENAME);

        HDF_READ_DATA(f, "/dat1D","d1d",&read_d1d);
        for(int i = 0; i < 10;i++){
                fprintf(stdout,"%d %f\n",i,read_d1d[i]);
        }
        gfree(read_d1d);
        HDF_READ_DATA(f, "/dat2D","d2d",&read_d2d);
        for(int i = 0; i < 3;i++){
                for(int j = 0; j < 3;j++){
                        fprintf(stdout,"%d %d %f\n",i,j,read_d2d[i][j]);
                }
        }
        gfree(read_d2d);

        HDF_READ_DATA(f, "/dat0D","d1d",&read_t);

        fprintf(stdout,"%d\n",(int)read_t );

        /* LOG_MSG("Build tree!"); */
        /* hdf5_build_tree(f); */

        /* HDF_READ_VALUE(f,"/dat0D","d1d",&read_t); */

        /* RUN(hdf5_print_tree(f-> , 0)); */

        if(hdf5_data_exists(f,"Donkey",&hdf_path) == OK){
                LOG_MSG("Donkey found: %s", hdf_path);
        }

        if(hdf5_data_exists(f,"d1d",&hdf_path) == OK){
                LOG_MSG("d1d found : %s", hdf_path);
        }

        if(hdf5_data_exists(f,"/dat1D/d1d",&hdf_path) == OK){
                LOG_MSG("d1d found : %s", hdf_path);
        }

        if(hdf5_data_exists(f,"d2d",&hdf_path) == OK){
                LOG_MSG("d2d found : %s", hdf_path);
        }


        tld_hdf5_close_file(&f);
        LOG_MSG("%d", read_t);

        gfree(d1d);
        gfree(d2d);

        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;
}
