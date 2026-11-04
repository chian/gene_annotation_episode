#include "alloc/tld-alloc.h"
#include "core/tld-core.h"
#include "stats/basic.h"
#include "tld.h"
#include <math.h>
#include <stdio.h>

static int calculate_seq_shannon(struct tl_seq* s,double* ret);
int main(int argc, char *argv[])
{
        FILE* f_ptr = NULL;
        struct file_handler* f = NULL;
        struct tl_seq_buffer* sb = NULL;
        double shannon = 0.0;
        if(argc > 2){
                f_ptr = fopen(argv[2], "w");
        }else{
                f_ptr = stdout;
        }
        double* dat = NULL;
        int n_dat = 0;
        galloc(&dat,1000000);

        if(argc > 1){
                RUN(open_fasta_fastq_file(&f, argv[1], TLSEQIO_READ));
                while(1){
                        RUN(read_fasta_fastq_file(f, &sb, 1000));
                        //detect_format(sb);
                        //total_r+= sb->num_seq;
                        LOG_MSG("Finished reading chunk: found %d ",sb->num_seq);
                        if(sb->num_seq == 0){
                                break;
                        }
                        for(int i = 0; i < sb->num_seq;i++){
                                sb->sequences[i]->len = MACRO_MIN(sb->sequences[i]->len,25);
                                calculate_seq_shannon(sb->sequences[i],&shannon);
                                fprintf(f_ptr,"%f\n", shannon);
                                if(n_dat!= 1000000){
                                        dat[n_dat] = shannon;
                                        n_dat++;
                                }

                        }
                }
        }

        if(n_dat > 0){
                double mean;
                tld_mean(dat, n_dat, &mean);
                double var;
                tld_sample_variance(dat, n_dat, &var);
                var = sqrt(var);
                LOG_MSG("ndat: %d %f %f",n_dat, mean, var);
                double x = 3.14;
                double p = 0;
                tld_normal_pdf(x,mean, var,&p);

                LOG_MSG("%f %f", x, p);
        }
        gfree(dat);
        free_tl_seq_buffer(sb);
        RUN(close_seq_file(&f));
        if(argc > 2){
                fclose(f_ptr);
        }
        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;
}

int calculate_seq_shannon(struct tl_seq* s,double* ret)
{

        double dist[256];
        double shannon = 0.0;
        uint8_t* seq = s->seq->str;
        for(int i = 0; i < 256;i++){
                dist[i] = 0.0;
        }
        for(int i = 0; i < s->len;i++){
                dist[seq[i]]++;
        }

        tld_shannon(dist,256,&shannon);

        *ret = shannon;
        return OK;
}
