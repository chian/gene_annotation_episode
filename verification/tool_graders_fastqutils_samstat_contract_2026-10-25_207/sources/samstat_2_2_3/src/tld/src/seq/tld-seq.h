#ifndef TLD_SEQ_H
#define TLD_SEQ_H

#include "../core/tld-core.h"
#include "../string/str.h"

#define ALIGN64 64
struct tl_seq{
        tld_strbuf* seq;
        tld_strbuf* name;
        tld_strbuf* qual;
        /* char* name; */
        /* uint8_t* qual; */
        void* data;
        /* int malloc_len; */
        int len;
} __attribute__((aligned(ALIGN64)));

#undef ALIGN64

#define ALIGN64 64
struct tl_seq_buffer{
        struct tl_seq** sequences;
        void* data;
        int malloc_num;
        int offset;
        int base_quality_offset;
        int num_seq;
        int max_len;
        int is_fastq;
        int L;
} __attribute__((aligned(ALIGN64)));

#undef ALIGN64

/* Alphabet  */
#define TLALPHABET_DEFAULT_PROTEIN 1
#define TLALPHABET_DEFAULT_DNA 2
#define TLALPHABET_REDUCED_PROTEIN 3

#define TLALPHABET_NOAMBIGIOUS_PROTEIN 4
#define TLALPHABET_NOAMBIGUOUS_DNA 5

struct alphabet;
struct rng_state;

tld_external int create_alphabet(struct alphabet** alphabet, struct rng_state* rng,int type);

tld_external uint8_t tlalphabet_get_code (const struct alphabet* a, char c);
tld_external int convert_to_internal(struct alphabet* a, uint8_t* seq, int len);
//EXTERN int convert_to_external(struct alphabet* a, uint8_t* seq, int len);

tld_external void free_alphabet(struct alphabet* a);


/* File IO */
#define TLSEQIO_READ 0

#define TLSEQIO_WRITE 1
#define TLSEQIO_WRITE_GZIPPED 2

#define TLSEQIO_APPEND 3
#define TLSEQIO_APPEND_GZIPPED 4
/* internal stuff */
#define FILE_TYPE_UNDEFINED 3
#define FILE_TYPE_FASTA 1
#define FILE_TYPE_FASTQ 2

/* Finite state automata */

#define S_START 0
#define S_NAME 1
#define S_SEQ 2
#define S_Q_NEXT 3
#define S_Q 4


#define RS_UNDEFINED 0
#define RS_NAME 1
#define RS_SEQ 2
#define RS_SEQ_DONE 3
#define RS_QUAL 4
#define RS_QUAL_DONE 5


typedef struct file_handler file_handler;

tld_external int open_fasta_fastq_file(struct file_handler** fh,char* filename, int mode);
tld_external int open_sam_bam(struct file_handler** fh, char* filename, int mode);
tld_external int read_fasta_fastq_file(struct file_handler* fh, struct tl_seq_buffer** seq_buf, int num);
tld_external int close_seq_file(struct file_handler** fh);

tld_external int write_seq_buf(struct tl_seq_buffer* sb, struct file_handler* fh);

/* Sequence buffer  */
#define TL_SEQ_MAX_NAME_LEN 128
#define TL_SEQ_BUFFER_PROTEIN 20
#define TL_SEQ_BUFFER_DNA 4


tld_external int internal_detect_fasta_fastq(const char *b, int len, int *type);
tld_external int detect_format(struct tl_seq_buffer* sb);

tld_external int alloc_tl_seq_buffer(struct tl_seq_buffer** seq_buf, int size);
tld_external int resize_tl_seq_buffer(struct tl_seq_buffer* sb);
tld_external int reset_tl_seq_buffer(struct tl_seq_buffer* sb);
tld_external void free_tl_seq_buffer(struct tl_seq_buffer* sb);

tld_external int alloc_tl_seq(struct tl_seq** sequence);
tld_external int resize_tl_seq(struct tl_seq* s);
tld_external void free_tl_seq(struct tl_seq* sequence);


tld_external int reverse(uint8_t *s, int l);
tld_external int reverse_comp(uint8_t *s, int l);
tld_external int rev_comp_tl_seq(struct tl_seq* s);
#endif
