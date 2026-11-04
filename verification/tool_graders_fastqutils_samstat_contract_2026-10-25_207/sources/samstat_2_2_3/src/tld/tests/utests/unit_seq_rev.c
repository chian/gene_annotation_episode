#include "tld.h"
#include <stdint.h>
#include <stdio.h>

int main(void)
{
        uint8_t* seq = NULL;
        int len = 0;
        struct rng_state* rng = NULL;
        RUN(init_rng(&rng, 0));
        galloc(&seq,16);
        for(int s = 0; s < 8;s++){
                len = 5 + tl_random_int(rng, 10);
                for(int i = 0; i < len;i++){
                        seq[i] = "ACGTN"[tl_random_int(rng,5)];

                }
                seq[len ] =0;
                fprintf(stdout,"Seq %d: \n",s+1);
                fprintf(stdout,"%s - org \n",seq);
                RUN(reverse(seq,len));
                fprintf(stdout,"%s - reverse \n",seq);
                RUN(reverse(seq,len));
                RUN(reverse_comp(seq,len));
                fprintf(stdout,"%s - reverse comp\n",seq);
        }

        gfree(seq);
        return EXIT_SUCCESS;
ERROR:
        if(seq){
                gfree(seq);
        }
        return EXIT_FAILURE;
}
