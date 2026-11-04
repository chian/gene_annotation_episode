#include "tld-seq.h"
#include "tld-seq-tables.h"
#include <stdint.h>

int reverse(uint8_t *s, int l)
{
        uint8_t tmp;
        int first = 0;
        int last = l-1;

        if(l < 2){
                return OK;
        }
        while (first < last) {
                tmp = s[first];
                s[first] = s[last];
                s[last] = tmp;

                first += 1;
                last -= 1;
        }
        return OK;
}

int reverse_comp(uint8_t *s, int l)
{
        uint8_t tmp;
        int first = 0;
        int last = l-1;

        if(l == 0){
                return OK;
        }
        if(l == 1){
                s[0] = comp_table[s[0]];
                return OK;
        }

        while (first < last) {
                tmp = comp_table[s[first]];
                s[first] = comp_table[s[last]];
                s[last] = tmp;

                first += 1;
                last -= 1;
        }
        if(l % 2 == 1){
                s[l/2] = comp_table[s[l/2]];
        }
        return OK;
}

int rev_comp_tl_seq(struct tl_seq* s)
{
        if(s->seq){
                reverse_comp(s->seq->str, s->seq->len);
        }
        if(s->qual){
                reverse(s->qual->str, s->qual->len);
        }
        return OK;
}
