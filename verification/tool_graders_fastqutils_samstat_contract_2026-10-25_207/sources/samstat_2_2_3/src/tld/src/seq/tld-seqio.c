#include "tld-seq.h"
#include "tld-seq-tables.h"
#include "../alloc/tld-alloc.h"
#include "../misc/misc.h"
#include "../string/str.h"
#include "../stats/basic.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <zlib.h>

#define TLSEQIO_FASTA 1
#define TLSEQIO_FASTQ 2
#define TLSEQIO_GZIPPED 4


#define TL_READ_BUFF_LEN 256 //8388608
//#define TL_READ_BUFF_LEN 300
#define TL_OUT_LINE_LEN 70

#define TL_DEFAULT_COMPRESSION '1'

#define str(x)          # x
#define xstr(x)         str(x)


#define RUNP(EXP)                               \
        if((EXP) == NULL){                      \
                ERROR_MSG(ADDFAILED(EXP));      \
        }


struct file_handler{
        FILE* f_ptr;
        gzFile gz_f_ptr;
        uint8_t file_type;
        tld_strbuf* line_buf;
        int trans[5][5];
        char start_symbol;
        /* char* read_buffer; */
        int file_end;
        /* int bytes_read; */
        /* int pos; */
        int read_state;
        int write_state;
        int gz;
        int n_parse_error;
};

static int read_gz_line(struct file_handler *fh);
/* int read_gz_line2(struct file_handler *fh); */
/* static int read_gz_line(struct file_handler *fh, tld_strbuf *b); */
/* static int detect_fasta_fastq(const char* b, int len, int* type); */
static int write_fasta_fastq(struct tl_seq_buffer* sb, struct file_handler* fh);
/* static int read_sequences(struct file_handler*fh, struct tl_seq_buffer* sb, int num); */

static int parse_buf(struct file_handler *fh, struct tl_seq_buffer *sb, int num);
/* static int print_error_context(char* buf, int len, int point); */
static int finalize_read(struct file_handler *fh, struct tl_seq_buffer *sb);
/* static int parse_buf_fasta(struct file_handler* fh, struct tl_seq_buffer* sb,int num); */
/* static int parse_buf_fastq(struct file_handler* fh, struct tl_seq_buffer* sb,int num); */

/* static int read_file_contents(struct file_handler* fh); */

static int get_io_handler(struct file_handler** fh,const char* filename,int gz);
static void free_io_handler(struct file_handler* f);

static int write_fasta_to_buf(struct tl_seq* seq, char* buf, int* index,int* write_ok);
static int write_fastq_to_buf(struct tl_seq* seq, char* buf, int* index,int* write_ok);

int write_seq_buf(struct tl_seq_buffer* sb, struct file_handler* fh)
{
        RUN(write_fasta_fastq(sb,fh));
        return OK;
ERROR:
        return FAIL;
}

int open_fasta_fastq_file(struct file_handler** fh,char* filename, int mode)
{
        struct file_handler* f = NULL;
        int type = 0;
        /* int status; */


        if(mode == TLSEQIO_READ){
                ASSERT(tld_file_exists(filename) == OK,"File: %s does not exists",filename);
                RUN(get_io_handler(&f, filename, mode));
                /* RUN(read_file_contents(f)); */

                /* internal_detect_fasta_fastq(f->read_buffer , f->bytes_read, &type); */
                /* exit(0); */
                /* detect file type  */
                /* RUN(detect_fasta_fastq(f->read_buffer , f->bytes_read, &type)); */

                /* status = gzrewind(f->gz_f_ptr); */
                /* if(status){ */
                        /* ERROR_MSG("gzrewind failed"); */
                /* } */
                switch (type) {
                case FILE_TYPE_FASTA:
                        //LOG_MSG("Found fasta");
                        break;
                case FILE_TYPE_FASTQ:
                        //LOG_MSG("Found fastq");
                        break;
                case FILE_TYPE_UNDEFINED:
                        ERROR_MSG("Could not determine type of file: %s",filename);
                        break;

                default:
                        break;
                }
                f->file_type = type;
        }else{
                RUN(get_io_handler(&f, filename, mode));
        }
        *fh = f;
        return OK;
ERROR:
        free_io_handler(f);
        return FAIL;
}

int read_fasta_fastq_file(struct file_handler* fh, struct tl_seq_buffer** seq_buf, int num)
{
        struct tl_seq_buffer* sb = NULL;
        ASSERT(fh!= NULL, "No file handler");
        ASSERT(num > 0, "Need to read more than %d sequences",num);


        sb = *seq_buf;
        if(sb == NULL){
                //LOG_MSG("Allocating seqbuffer");
                RUN(alloc_tl_seq_buffer(&sb, num));
        }else{
                while(num > sb->malloc_num){
                        RUN(resize_tl_seq_buffer(sb));
                }
        }

        sb->is_fastq = 0;
        if(fh->file_type == FILE_TYPE_FASTQ){
                sb->is_fastq = 1;
        }

        RUN(reset_tl_seq_buffer(sb));

        /* LOG_MSG("Start read"); */
        /* read_gz_line2(fh); */
        /* reading  */

        RUN(parse_buf(fh,sb,num));
        RUN(finalize_read(fh, sb));
        /* RUN(read_sequences(fh,sb,num)); */

        /* if(sb->base_quality_offset == 0){ */
        /*         RUN(detect_format(sb)); */
        /* } */


        *seq_buf = sb;
        return OK;
ERROR:
        return FAIL;
}

/* int read_sequences(struct file_handler*fh, struct tl_seq_buffer* sb, int num) */
/* { */
/*         /\* int i; *\/ */
/*         /\* int max_len; *\/ */
/*         tld_strbuf* b = NULL; */
/*         /\* tld_append(tld_strbuf *b, char *content) *\/ */
/*         tld_strbuf_alloc(&b, 1024); */
/*         b->len = 0; */
/*         while(1){ */
/*                 RUN(read_gz_line(fh)); */

/*                 if(!b->len){ */
/*                         break; */
/*                 } */
/*                 fprintf(stdout,"%s\n",TLD_STR(b)); */
/*                 /\* b->len = 0; *\/ */
/*         } */


/*         tld_strbuf_free(b); */
/*         exit(0); */

/*         while(1){ */
/*                 LOG_MSG("fh->pos: %d",fh->pos); */
/*                 if(fh->pos){ */
/*                         LOG_MSG("Finishing buffer"); */
/*                         /\* if(fh->file_type == FILE_TYPE_FASTA){ *\/ */
/*                         /\*         RUN(parse_buf_fasta(fh,sb,num)); *\/ */
/*                         /\* }else if(fh->file_type == FILE_TYPE_FASTQ){ *\/ */
/*                         /\*         RUN(parse_buf_fastq(fh,sb,num)); *\/ */
/*                         /\* }else{ *\/ */
/*                         /\*         ERROR_MSG("Unknown file type"); *\/ */
/*                         /\* } *\/ */
/*                         RUN(parse_buf(fh,sb,num)); */
/*                         sb->num_seq++; */
/*                         /\* fh->read_state = S_START; *\/ */
/*                         if(sb->num_seq == num){ */
/*                                 break; */
/*                         } */
/*                 }else{ */
/*                         LOG_MSG("read new content"); */
/*                         if (gzeof (fh->gz_f_ptr)){ */
/*                                 /\* LOG_MSG("Nothing left"); *\/ */
/*                                 break; */
/*                         } */
/*                         RUN(read_file_contents(fh)); */
/*                         if(!fh->bytes_read){ */
/*                                 /\* LOG_MSG("Nothing left"); *\/ */
/*                                 break; */
/*                         } */
/*                         RUN(parse_buf(fh,sb,num)); */
/*                         sb->num_seq++; */
/*                         /\* fh->read_state = S_START; *\/ */
/*                         /\* if(fh->file_type == FILE_TYPE_FASTA){ *\/ */
/*                         /\*         RUN(parse_buf_fasta(fh,sb,num)); *\/ */
/*                         /\* }else if(fh->file_type == FILE_TYPE_FASTQ){ *\/ */
/*                         /\*         RUN(parse_buf_fastq(fh,sb,num)); *\/ */
/*                         /\* }else{ *\/ */
/*                         /\*         ERROR_MSG("Unknown file type"); *\/ */
/*                         /\* } *\/ */
/*                         if(sb->num_seq == num){ */
/*                                 break; */
/*                         } */
/*                 } */
/*         } */
/*         RUN(finalize_read(fh, sb)); */

/*         return OK; */
/* ERROR: */
/*         return FAIL; */
/* } */


int parse_buf(struct file_handler *fh, struct tl_seq_buffer *sb, int num)
{
        int state;
        int n_lines = 0;
        char c;

        /* int first_seq = 1; */
        ASSERT(fh!= NULL, "No file handler");
        ASSERT(sb!= NULL, "No sequence buffer");

        state = fh->read_state;

        while(1){
                if(!fh->line_buf->len){
                        RUN(read_gz_line(fh));
                }
                if(fh->line_buf->len == 0){
                        break;
                }
                uint8_t* line = fh->line_buf->str;

                /* LOG_MSG("%s",line); */
                /* for(i = pos;i < buf_len;i++){ */
                c = line[0];
                switch (state) {
                case S_START:
                        if(c == '@' || c == '>'){
                                fh->start_symbol = c;
                                fh->trans[S_START][S_NAME]++;
                                state = S_NAME;
                                RUN(tld_strbuf_copy(sb->sequences[sb->num_seq]->name, fh->line_buf));
                        }
                        break;
                case S_NAME:
                        if(is_aa[(uint8_t) c] || is_nuc[(uint8_t)c]){
                                fh->trans[S_NAME][S_SEQ]++;
                                state = S_SEQ;
                                RUN(tld_strbuf_copy(sb->sequences[sb->num_seq]->seq, fh->line_buf));
                                sb->sequences[sb->num_seq]->len = sb->sequences[sb->num_seq]->seq->len;
                        }else if(c != 0){
                                fh->n_parse_error++;
                                ERROR_MSG("%d: A name line is not followed by a sequence line. %s",fh->n_parse_error,TLD_STR(fh->line_buf));
                        }
                        break;
                case S_SEQ:
                        if(is_aa[(uint8_t) c] || is_nuc[(uint8_t)c]){
                                fh->trans[S_SEQ][S_SEQ]++;
                                state = S_SEQ;
                                RUN(tld_append(sb->sequences[sb->num_seq]->seq, TLD_STR(fh->line_buf)));

                                sb->sequences[sb->num_seq]->len = sb->sequences[sb->num_seq]->seq->len;
                        }else if(c == fh->start_symbol){

                                sb->num_seq++;
                                if(sb->num_seq == num){
                                        fh->read_state = S_START;//state;
                                        return OK;
                                }
                                fh->trans[S_SEQ][S_NAME]++;
                                state = S_NAME;
                                RUN(tld_strbuf_copy(sb->sequences[sb->num_seq]->name, fh->line_buf));
                        }else if(c == '+'){
                                fh->trans[S_SEQ][S_Q_NEXT]++;
                                state = S_Q_NEXT;
                        }else if(c != 0){
                                fh->n_parse_error++;
                                ERROR_MSG("%d: Don't understand - was in a seq and expecting more sequences, a '+' line or a name: %s",
                                          fh->n_parse_error,TLD_STR(fh->line_buf) );
                        }
                        break;
                case S_Q_NEXT:
                        /* range of quality encodings for pacbio (coversillumina18 intervals) */
                        if(c >= 33 && c <= 126){
                                fh->trans[S_Q_NEXT][S_Q]++;
                                state = S_Q;
                                RUN(tld_strbuf_copy(sb->sequences[sb->num_seq]->qual, fh->line_buf));
                        }else{
                                fh->n_parse_error++;
                                ERROR_MSG("%d: Line following a '^+' line does not start with a valid base quality: %c",
                                          fh->n_parse_error,TLD_STR(fh->line_buf));
                        }
                        break;
                case S_Q:
                        if(c == fh->start_symbol){

                                sb->num_seq++;

                                if(sb->num_seq == num){
                                        fh->read_state = S_START;
                                        return OK;
                                }

                                fh->trans[S_Q][S_NAME]++;
                                state = S_NAME;
                                RUN(tld_strbuf_copy(sb->sequences[sb->num_seq]->name, fh->line_buf));
                        }else if(c != 0){
                                fh->n_parse_error++;
                                WARNING_MSG("%s", TLD_STR(sb->sequences[sb->num_seq]->name));
                                WARNING_MSG("%d", c);
                                ERROR_MSG("%d: A base quality line is not followed by a sequence line.: %s",
                                          fh->n_parse_error,TLD_STR(fh->line_buf));
                        }
                        break;
                }
                fh->line_buf->len = 0;
                n_lines++;
        }

        if(n_lines){
                sb->num_seq++;
        }
        return OK;
ERROR:
        return FAIL;
}

int finalize_read(struct file_handler *fh, struct tl_seq_buffer *sb)
{
        struct tl_seq* s = NULL;
        double*  dist = NULL;
        int max_len = -1;
        int n_is_dna = 0;
        int n_is_aa = 0;
        if(fh->n_parse_error){
                /* sb->num_seq = 0; */
                return FAIL;
                /* *type = FILE_TYPE_UNDEFINED; */
        }else{
                if(fh->trans[S_START][S_NAME] == 0){
                        WARNING_MSG("Could not detect a single sequence name.");
                        if(sb->num_seq){
                                WARNING_MSG("Even stranger - the parser did record a sequence");
                        }
                        /* sb->num_seq = 0; */
                        return FAIL;
                }else if(fh->trans[S_START][S_NAME] && fh->trans[S_NAME][S_SEQ] == 0){
                        WARNING_MSG("Could detect a name but no sequence.");
                        if(sb->num_seq){
                                WARNING_MSG("Even stranger - the parser did record a sequence");
                        }
                        /* sb->num_seq = 0; */
                        return FAIL;
                }else if(fh->trans[S_SEQ][S_Q_NEXT] && fh->trans[S_Q_NEXT][S_Q] == 0){
                        WARNING_MSG("Could detect (at least) a sequence that should have base qualities but found none .");
                        /* sb->num_seq = 0; */
                        return FAIL;
                }else if(fh->trans[S_SEQ][S_Q_NEXT] ){
                        sb->is_fastq = 1;
                }else{
                        sb->is_fastq = 0;
                }
        }
        sb->base_quality_offset = 0;


        galloc(&dist, 256);
        for(int i = 0; i < 256;i++){
                dist[i] = 0.0;
        }

        for(int i = 0; i < sb->num_seq;i++){
                s = sb->sequences[i];
                uint8_t* seq = s->seq->str;
                /* LOG_MSG("%d %d",s->len, s->seq->len); */
                for(int j = 0; j < s->len;j++){
                        if(is_nuc[seq[j]]){
                                n_is_dna++;
                        }
                        if(is_aa[seq[j]]){
                                n_is_aa++;
                        }
                        if(seq[j] < 33 ){
                                LOG_MSG("Weird character found : %d at position %d in seq %d", seq[j], j , i);
                        }
                        dist[seq[j]]++;
                }
                if(n_is_dna > 1000000 || n_is_aa > 1000000){
                        break;
                }
        }

        for(int i = 0; i < sb->num_seq;i++){
                s = sb->sequences[i];
                /* more sanity checks */
                if(sb->is_fastq){
                        /* LOG_MSG("%d %s %d %d",i,TLD_STR(s->name), s->seq->len,s->qual->len); */
                        if(s->seq->len != s->qual->len){
                                WARNING_MSG("Length of sequence %d (%s) is not equal to length of base qualities.: %d seq %d qual",i, TLD_STR(s->name), s->seq->len,s->qual->len);

                                fprintf(stdout,"%s\n%s\n", s->seq->str, s->qual->str);
                                return FAIL;
                                /* sb->num_seq = 0; */
                        }
                }

                /* LOG_MSG("%d %d %d", max_len, s->len,s->seq->len); */
                if(s->len > max_len){
                        max_len = s->len;
                }
        }
        /* LOG_MSG("%d %d",n_is_dna, n_is_aa); */
        if(sb->num_seq){
                if(n_is_aa > n_is_dna){
                        sb->L = TL_SEQ_BUFFER_PROTEIN;
                }else{
                        double shannon = 0.0;
                        double p1 = 0.0;
                        double p2 = 0.0;
                        double sum = 0.0;

                        tld_shannon(dist,256,&shannon);
                        /* Magical numbers ahead to see whether the shannon entropy
                           of the letter distribution matches nucleotide or protein
                           sequences patterns.
                         */
                        /* mean and standard deviation of shannon entropy
                           of first 25 nucleotide of sequences in:
                           uniprot_sprot.fasta.gz
                        */
                        tld_normal_pdf(shannon, 3.454989,0.257477,&p1);

                        /* mean and standard deviation of shannon entropy
                           of first 25 nucleotide of sequences in:
                           vertebrate_mammalian.1.rna.fna.gz
                        */
                        tld_normal_pdf(shannon, 1.838894,0.138224,&p2);

                        sum = p1 + p2;
                        p1 = p1 / sum;
                        p2 = p2 / sum ;
                        /* LOG_MSG("%d %d  protein: %f nuc: %f",n_is_dna,n_is_aa, p1, p2); */
                        if(p1 > p2){
                                sb->L = TL_SEQ_BUFFER_PROTEIN;
                        }else{
                                sb->L = TL_SEQ_BUFFER_DNA;
                        }
                }
        }
        /* LOG_MSG("is: %d", sb->L); */
        sb->offset = 33;
        sb->max_len = max_len;
        gfree(dist);
        /* exit(0); */
        return OK;
ERROR:
        if(dist){
                gfree(dist);
        }
        return FAIL;
}

/* int get_base_q_offset(struct tl_seq* s, int* offset) */
/* { */
/*         /\* */
/*            SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS..................................................... */
/*            ..........................XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX...................... */
/*            ...............................IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII...................... */
/*            .................................JJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJ..................... */
/*            LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL.................................................... */
/*            PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP */
/*            !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~ */
/*            |                         |    |        |                              |                     | */
/*           33                        59   64       73                            104                   126 */
/*            0........................26...31.......40                                 S - Sanger  Phred+33 */
/*                                     -5....0........9.............................40  X - Solexa    Solexa+64 */
/*                                           0........9.............................40  I - Illumina 1.3+ */
/*                                              3.....9..............................4  J - Illumina 1.5+ */
/*            0.2......................26...31........41                                L - Illumina 1.8+ */
/*            0..................20........30........40........50..........................................93  P - PacBio */
/*         *\/ */
/*         char q_type[] = "SXIJLP"; */
/*         uint32_t count[6] = {0,0,0,0,0,0}; */
/*         uint8_t c = 0; */
/*         for(int i = 0; i < s->qual->len;i++){ */
/*                 c = s->qual->str[i]; */
/*                 if(c >= 33 && c < 59){ */
/*                         count[0]++; */
/*                         count[4]++; */
/*                         count[5]++; */
/*                 }else if(c >=59 && c < 64){ */

/*                 } */
/*         } */

/*         return OK; */

/* } */

int close_seq_file(struct file_handler** fh)
{
        if(*fh){
                free_io_handler(*fh);
                *fh = NULL;
        }
        return OK;
}


int get_io_handler(struct file_handler** fh,const char* filename,int mode)
{
        struct file_handler* f_handle = NULL;
        char* ret = NULL;
        char file_mode[4];
        gzFile local_gz_f_ptr = NULL;


        //ASSERT(my_file_exists(filename), "File: %s not found.", filename);

        /* This is a bit ugly - refine in future. */
        if(!*fh){
                MMALLOC(f_handle, sizeof(struct file_handler));
        }
        f_handle->f_ptr = NULL;
        f_handle->gz_f_ptr = NULL;
        f_handle->file_type = 0;
        f_handle->file_end = 0;
        /* f_handle->read_buffer = NULL; */
        /* f_handle->bytes_read = 0; */
        /* f_handle->pos = 0; */
        f_handle->read_state = S_START ; // RS_UNDEFINED;
        f_handle->write_state = 0;
        f_handle->gz= 0;
        f_handle->n_parse_error = 0;
        f_handle->start_symbol = 0;
        f_handle->line_buf = NULL;

        RUN(tld_strbuf_alloc(&f_handle->line_buf, 1024*1024));

        for(int i = 0 ; i < 5; i++){
                for(int j = 0 ; j < 5; j++){
                        f_handle->trans[i][j] = 0;
                }
        }

        /* MMALLOC(f_handle->read_buffer, sizeof(char)*  TL_READ_BUFF_LEN + TL_READ_BUFF_LEN); */

        ret = strstr(filename, "fasta");
        if(ret){
                f_handle->file_type += TLSEQIO_FASTA;
        }
        ret = strstr(filename, "fastq");
        if(ret){
                f_handle->file_type+= TLSEQIO_FASTQ;
        }
        ret = strstr(filename, "gz");
        if(ret){
                if(strlen(ret) == 2){
                        /* LOG_MSG("Is gzipped"); */
                        f_handle->file_type |= TLSEQIO_GZIPPED;
                }
        }
        if(mode == TLSEQIO_WRITE){
                if(f_handle->file_type & TLSEQIO_GZIPPED){
                        WARNING_MSG("Opening an file for uncompressed write was requested but the file ends in .gz");
                        WARNING_MSG("Will write compressed. Consider using the TLSEQIO_WRITE_GZIPPED!");
                        file_mode[0] = 'w';
                        file_mode[1] = 'b';
                        file_mode[2] = TL_DEFAULT_COMPRESSION;
                        file_mode[3] = 0;

                        RUNP(local_gz_f_ptr = gzopen(filename, file_mode));

                        f_handle->gz = 1;
                }else{
                        //LOG_MSG("Opening file %s for writing",filename);
                        file_mode[0] = 'w';
                        file_mode[1] = 0;
                        RUNP(f_handle->f_ptr = fopen(filename, file_mode));
                        f_handle->gz = 0;
                }
        }
        if(mode == TLSEQIO_WRITE_GZIPPED){
                //LOG_MSG("Opening file %s for writing",filename);
                file_mode[0] = 'w';
                file_mode[1] = 'b';
                file_mode[2] = TL_DEFAULT_COMPRESSION;
                file_mode[3] = 0;

                RUNP(local_gz_f_ptr= gzopen(filename, file_mode));
                f_handle->gz = 1;
        }

        if(mode == TLSEQIO_APPEND){
                if(f_handle->file_type & TLSEQIO_GZIPPED){
                        WARNING_MSG("Opening an file for uncompressed append was requested but the file ends in .gz");
                        WARNING_MSG("Will write compressed. Consider using the TLSEQIO_WRITE_GZIPPED!");
                        file_mode[0] = 'a';
                        file_mode[1] = 'b';
                        file_mode[2] = TL_DEFAULT_COMPRESSION;
                        file_mode[3] = 0;

                        RUNP(local_gz_f_ptr = gzopen(filename, file_mode));

                        f_handle->gz = 1;
                }else{
                        //LOG_MSG("Opening file %s for writing",filename);
                        file_mode[0] = 'a';
                        file_mode[1] = 0;
                        RUNP(f_handle->f_ptr = fopen(filename, file_mode));
                        f_handle->gz = 0;
                }
        }
        if(mode == TLSEQIO_APPEND_GZIPPED){
                //LOG_MSG("Opening file %s for writing",filename);
                file_mode[0] = 'a';
                file_mode[1] = 'b';
                file_mode[2] = TL_DEFAULT_COMPRESSION;
                file_mode[3] = 0;

                RUNP(local_gz_f_ptr= gzopen(filename, file_mode));
                f_handle->gz = 1;
        }

        if(mode == TLSEQIO_READ){
                file_mode[0] = 'r';
                file_mode[1] = 0;

                //LOG_MSG("Opening %s for reading (%s)", filename,file_mode);
                RUNP(local_gz_f_ptr = gzopen(filename, file_mode));
                     //fprintf(stdout,"%p\n",(void*) local_gz_f_ptr);

        }

        f_handle->gz_f_ptr = local_gz_f_ptr;

        *fh = f_handle;
        return OK;
ERROR:
        return FAIL;
}

void free_io_handler(struct file_handler* f)
{
        if(f){
                if(f->line_buf){
                        tld_strbuf_free(f->line_buf);
                }
                if(f->gz_f_ptr){
                        gzclose(f->gz_f_ptr);
                }
                if(f->f_ptr){
                        fclose(f->f_ptr);
                }
                /* if(f->read_buffer){ */
                        /* MFREE(f->read_buffer); */
                /* } */
                MFREE(f);
        }
}

/* int echo_file(struct file_handler* f) */
/* { */
/*         char* buf = NULL; */

/*         buf = f->read_buffer; */
/*         while (1) { */
/*                 int bytes_read; */
/*                 bytes_read = gzread ( f->gz_f_ptr, buf,  TL_READ_BUFF_LEN - 1); */
/*                 buf[bytes_read] = '\0'; */
/*                 //printf ("%s", buf); */
/*                 LOG_MSG("Read: %d", bytes_read); */
/*                 if (bytes_read < TL_READ_BUFF_LEN - 1) { */
/*                         LOG_MSG("Read: %d", bytes_read); */
/*                         if (gzeof (f->gz_f_ptr )) { */
/*                                 break; */
/*                         }else{ */
/*                                 ERROR_MSG("Something went wrong"); */
/*                         } */
/*                 } */
/*         } */
/*         return OK; */
/* ERROR: */
/*         return FAIL; */
/* } */

int read_gz_line(struct file_handler *fh)
{
        tld_strbuf* b = NULL;
        b = fh->line_buf;
        b->len = 0;

        gzgets (fh->gz_f_ptr, TLD_STR(b), b->alloc_len);

        if(!gzeof(fh->gz_f_ptr)){
                b->len = strlen(TLD_STR(b));
                if(b->str[b->len-1] == '\n'){
                        b->str[b->len-1]  = 0;
                        b->len--;
                }
                if(b->str[b->len-1] == '\r'){
                        b->str[b->len-1]  = 0;
                        b->len--;
                }
                /* LOG_MSG("%d", b->str[b->len-1]); */
        }
        return OK;
}

/* int read_gz_line2(struct file_handler *fh) */
/* { */
/*         tld_strbuf* b = NULL; */
/*         int c; */

/*         b = fh->line_buf; */
/*         b->len = 0; */
/*         if(gzeof(fh->gz_f_ptr)){ */
/*                 b->len = 0; */
/*                 return OK; */
/*         } */
/*         while (1){ */
/*                 c = gzgetc (fh->gz_f_ptr); */

/*                 if(c == '\n'){ */
/*                         break; */
/*                 }else if(c == EOF){ */
/*                         break; */
/*                 }else if( c == '\r'){ */
/*                 }else { */
/*                         tld_append_char(b, c); */
/*                 } */
/*         } */
/*         return OK; */
/* } */


/* Memory functions  */
/* int read_file_contents(struct file_handler* fh) */
/* { */
/*         int c; */
/*         int n_read; */
/*         ASSERT(fh!=NULL, "No file handler"); */

/*         n_read = gzread(fh->gz_f_ptr, fh->read_buffer, TL_READ_BUFF_LEN -1); */

/*         if(!n_read){ */
/*                 int zlib_status = 0; */
/*                 const char* error =  gzerror (fh->gz_f_ptr, &zlib_status); */
/*                 switch (zlib_status) { */
/*                 case Z_STREAM_END: */
/*                 case Z_OK: */
/*                         fh->file_end = 1; */
/*                         break; */
/*                 case Z_ERRNO: */
/*                         ERROR_MSG("%s",error); */
/*                         break; */
/*                 default: */
/*                         ERROR_MSG("%s",error); */
/*                         break; */
/*                 } */
/*         } */
/*         fh->file_end = gzeof(fh->gz_f_ptr); */

/*         fh->bytes_read = n_read; */
/*         fh->read_buffer[fh->bytes_read] = 0; */
/*         fh->pos = 0; */

/*         fprintf(stdout,"END? %d\n", fh->file_end); */
/*         /\* fprintf(stdout,"%s", fh->read_buffer); *\/ */
/*         /\* Read more bytes  until we have a newline *\/ */
/*         if(fh->read_buffer[fh->bytes_read-1] != '\n'){ */
/*                 while(1){ */
/*                         c = gzgetc(fh->gz_f_ptr); */
/*                         fh->read_buffer[fh->bytes_read] = c; */
/*                         fh->bytes_read++; */
/*                         if(c == '\n' || c == EOF){ */
/*                                 break; */
/*                         } */
/*                 } */
/*         } */
/*         fh->file_end = gzeof(fh->gz_f_ptr); */

/*         fprintf(stdout,"END? %d\n", fh->file_end); */
/*         /\* LOG_MSG("LAst char: %d",  fh->read_buffer[fh->bytes_read-1]); *\/ */
/*         fh->read_buffer[fh->bytes_read] = 0; */
/*         /\* exit(0); *\/ */
/*         fprintf(stdout,"%s", fh->read_buffer); */
/*         return OK; */
/* ERROR: */
/*         return FAIL; */
/* } */


int write_fasta_fastq(struct tl_seq_buffer* sb, struct file_handler* fh)
{
        char* write_buffer = NULL;
        int wb_pos;
        int i;
        int write_ok;
        /* function pointer to switch between fasta and fastq output */
        int (*write_p)(struct tl_seq* seq, char* buf, int* index,int* write_ok) = NULL;

        ASSERT(sb != NULL, "No sequence buffer");

        wb_pos = 0;
        MMALLOC(write_buffer, sizeof(char) * TL_READ_BUFF_LEN);

        if(sb->is_fastq){
                write_p = &write_fastq_to_buf;
        }else{
                write_p = &write_fasta_to_buf;
        }

        for(i = 0; i < sb->num_seq;i++){
                RUN(write_p(sb->sequences[i],write_buffer, &wb_pos,&write_ok));
                if(!write_ok){
                        if(fh->gz){
                                gzwrite(fh->gz_f_ptr, write_buffer, wb_pos);
                        }else{
                                fwrite(write_buffer, sizeof(char), wb_pos,fh->f_ptr);
                        }
                        wb_pos = 0;
                        RUN(write_p(sb->sequences[i],write_buffer, &wb_pos,&write_ok));
                        if(!write_ok){
                                ERROR_MSG("Couldn't fit sequence into write buffer(!)");
                        }
                }
        }
        if(wb_pos){
                if(fh->gz){
                        gzwrite(fh->gz_f_ptr, write_buffer, wb_pos);
                }else{
                        fwrite(write_buffer, sizeof(char), wb_pos,fh->f_ptr);
                }
        }
        MFREE(write_buffer);
        return OK;
ERROR:
        return FAIL;
}

int write_fasta_to_buf(struct tl_seq* seq, char* buf, int* index,int* write_ok)
{
        int name_len;
        int len;
        int i;
        int local_i;
        int check;

        local_i = *index;
        /* length of name; plus one for '>' plus one for newline  */
        name_len = TLD_STRLEN(seq->name);//  strnlen(seq->name, TL_SEQ_MAX_NAME_LEN);
        len = name_len +2;
        /* length of sequence + one for newline + len / 70 for internal line breaks  */
        len += seq->len + 1 + seq->len / TL_OUT_LINE_LEN;
        /* plus one character for the null terminator  */
        len += 1;
        *write_ok = 1;
        /* does this fit?  */
        if(local_i + len >= TL_READ_BUFF_LEN){
                *write_ok = 0;
                return OK;
        }

        check = local_i;
        buf[local_i] = '>';
        local_i++;
        for(i = 0;i < name_len;i++){
                buf[local_i] = TLD_STR(seq->name)[i]; //TLD_S  seq->name[i];
                local_i++;
        }
        buf[local_i] = '\n';
        local_i++;
        /* write sequence */
        for(i = 0;i < seq->len;i++){
                if((i!=0) && (i % TL_OUT_LINE_LEN) == 0){
                        buf[local_i] = '\n';
                        local_i++;
                }
                buf[local_i] = TLD_STR(seq->seq)[i];
                local_i++;
        }
        buf[local_i] = '\n';
        local_i++;

        buf[local_i] = 0;

        check = (local_i+1) - check;
        ASSERT(check == len, "Wrote %d but estimated %d", check,len);
        *index = local_i;
        return OK;
ERROR:
        return FAIL;
}


int write_fastq_to_buf(struct tl_seq* seq, char* buf, int* index,int* write_ok)
{
        int name_len;
        int len;
        int i;
        int local_i;
        int check;

        local_i = *index;
        /* length of name; plus one for '>' plus one for newline  */
        name_len =  TLD_STRLEN(seq->name);//  strnlen(seq->name, TL_SEQ_MAX_NAME_LEN);
        len = name_len +2;
        /* length of sequence + one for newline*/
        len += seq->len + 1 ;
        /* add two for '+' and newline */
        len += 2;
        /* same again for the base quality  */
        len += seq->len + 1 ;
        /* plus one character for the null terminator  */
        len += 1;
        *write_ok = 1;
        /* does this fit?  */
        if(local_i + len >= TL_READ_BUFF_LEN){
                *write_ok = 0;
                return OK;
        }

        check = local_i;
        buf[local_i] = '@';
        local_i++;
        for(i = 0;i < name_len;i++){
                buf[local_i] =  TLD_STR(seq->name)[i];//  seq->name[i];
                local_i++;
        }
        buf[local_i] = '\n';
        local_i++;
        /* write sequence */
        for(i = 0;i < seq->len;i++){
                buf[local_i] = TLD_STR(seq->seq)[i];
                local_i++;
        }
        buf[local_i] = '\n';
        local_i++;

        buf[local_i] = '+';
        local_i++;
        buf[local_i] = '\n';
        local_i++;

        for(i = 0;i < seq->len;i++){
                buf[local_i] = TLD_STR(seq->qual)[i];
                local_i++;
        }
        buf[local_i] = '\n';
        local_i++;

        buf[local_i] = 0;

        check = (local_i+1) - check;
        ASSERT(check == len, "Wrote %d but estimated %d", check,len);

        *index = local_i;
        return OK;
ERROR:
        return FAIL;
}
