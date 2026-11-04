#include "tld-seq.h"
#include "tld-seq-tables.h"
#include <stdint.h>


static int get_char_at_line_start(const char *b, int len, int *pos, char *c);
/* The purpose is just to distringuish between fasta / fastq  */
int internal_detect_fasta_fastq(const char *b, int len, int *type)
{
        /* uint8_t  */
        int b_pos = 0;
        uint8_t state = S_START;
        char c;
        char name_symbol;
        int parse_error = 0;
        int trans[5][5] = {
                {0,0,0,0,0},
                {0,0,0,0,0},
                {0,0,0,0,0},
                {0,0,0,0,0},
                {0,0,0,0,0}
        };
        /* const char state_names[5][10] = { */
        /*         "START", */
        /*         "NAME", */
        /*         "SEQ", */
        /*         "Q+", */
        /*         "Q" */
        /* }; */

        state = S_START;
        b_pos = 0;
        while(b_pos < len){
                RUN(get_char_at_line_start(b, len, &b_pos, &c));
                switch (state) {
                case S_START:
                        if(c == '@' || c == '>'){
                                name_symbol = c;
                                trans[S_START][S_NAME]++;
                                state = S_NAME;
                        }
                        break;
                case S_NAME:
                        if(is_aa[(uint8_t) c] || is_nuc[(uint8_t)c]){
                                trans[S_NAME][S_SEQ]++;
                                state = S_SEQ;
                        }else if(c != 0){
                                parse_error++;
                                WARNING_MSG("ERROR %d: A name line is not followed by a sequence line.",parse_error);

                        }
                        break;
                case S_SEQ:
                        if(is_aa[(uint8_t) c] || is_nuc[(uint8_t)c]){
                                trans[S_SEQ][S_SEQ]++;
                                state = S_SEQ;
                        }else if(c == name_symbol){
                                trans[S_SEQ][S_NAME]++;
                                state = S_NAME;
                        }else if(c == '+'){
                                trans[S_SEQ][S_Q_NEXT]++;
                                state = S_Q_NEXT;
                        }else if(c != 0){
                                parse_error++;
                                WARNING_MSG("ERROR %d: Don't understand - was in a seq and expecting more sequencuens, a '+' line or a name: %c",parse_error,c);
                        }
                        break;
                case S_Q_NEXT:
                        /* range of quality encodings for pacbio (coversillumina18 intervals) */
                        if(c >= 33 && c <= 126){
                                trans[S_Q_NEXT][S_Q]++;
                                state = S_Q;
                        }else{
                                parse_error++;
                                WARNING_MSG("ERROR %d: Line following a '^+' line does not start with a valid base quality: %c",parse_error,c);
                        }
                        break;
                case S_Q:
                        if(name_symbol){
                                trans[S_Q][S_NAME]++;
                                state = S_NAME;
                        }else if(c != 0){
                                parse_error++;
                                WARNING_MSG("ERROR %d: A base quality line is not followed by a sequence line.: %c",parse_error,c);
                        }
                        break;
                }
                /* LOG_MSG("%c at %d (%d), state : %d", c, b_pos,len,state); */
        }
        /* Analysis of results */
        if(parse_error){
                *type = FILE_TYPE_UNDEFINED;
        }else{
                if(trans[S_START][S_NAME] == 0){
                        WARNING_MSG("Could not detect a single sequence name.");
                }else if(trans[S_START][S_NAME] && trans[S_NAME][S_SEQ] == 0){
                        WARNING_MSG("Could detect a name but no sequence.");
                }else if(trans[S_SEQ][S_Q_NEXT] && trans[S_Q_NEXT][S_Q] == 0){
                        WARNING_MSG("Could detect (at least) a sequence that should have base qualities but found none .");
                }else if(trans[S_SEQ][S_Q_NEXT] ){
                        *type = FILE_TYPE_FASTQ;
                }else{
                        *type = FILE_TYPE_FASTQ;
                }
        }
        /* for(int i = 0; i < 5; i++){ */
        /*         for(int j = 0; j < 5;j++){ */
        /*                 if(trans[i][j]){ */
        /*                         LOG_MSG("%s -> %s : %d", state_names[i], state_names[j], trans[i][j]); */
        /*                 } */
        /*         } */
        /* } */
        /* exit(0); */

        return OK;
ERROR:
        return FAIL;
}

int get_char_at_line_start(const char *b, int len, int *pos, char *c)
{
        int p = *pos;
        if(p == 0){
                *c = b[p];
                *pos = p+1;
                return OK;
        }

        while(b[p] != '\n' && p != len){
                p++;
        }
        /* LOG_MSG("scrolling: %d %d ", p, len); */
        if(p + 1 == len){
                *c = 0;
                *pos = len;
                return OK;
        }
        p++;
        *c = b[p];
        *pos = p+1;
        return OK;
}
