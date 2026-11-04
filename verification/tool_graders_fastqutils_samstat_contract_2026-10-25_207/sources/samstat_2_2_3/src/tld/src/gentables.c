#include "tld.h"

static int header(tld_strbuf *b);
static int footer(tld_strbuf *b);
static int create_is_aa_table(tld_strbuf *b);
static int create_is_nuc_table(tld_strbuf *b);
static int create_rev_comp_table(tld_strbuf* b);


int main(int argc, char *argv[])
{
        tld_strbuf* b = NULL;
        FILE* f_ptr = NULL;
        if(argc != 2){
                ERROR_MSG("This helper program requires exactly one argument - the name of an output file.");
        }

        tld_strbuf_alloc(&b,1024);
        RUN(header(b));
        RUN(create_is_aa_table(b));
        RUN(create_is_nuc_table(b));
        RUN(create_rev_comp_table(b));
        RUN(footer(b));
        f_ptr = fopen(argv[1], "w");
        if(f_ptr == NULL){
                ERROR_MSG("Unable to open file %s for writing.", argv[1]);
        }
        fprintf(f_ptr,"%s", TLD_STR(b));

        fclose(f_ptr);

        tld_strbuf_free(b);

        return EXIT_SUCCESS;
ERROR:
        if(f_ptr){
                fclose(f_ptr);
        }
        if(b){
                tld_strbuf_free(b);
        }
        return EXIT_FAILURE;
}

int header(tld_strbuf *b)

{
        RUN(tld_append(b, "#ifndef TLD_SEQ_TABLES\n"));
        RUN(tld_append(b, "#define TLD_SEQ_TABLES\n"));
        RUN(tld_append(b, "#include <stdint.h>\n"));
        return OK;
ERROR:
        return FAIL;
}
int footer(tld_strbuf *b)
{
        RUN(tld_append(b, "#endif\n"));
        return OK;
ERROR:
        return FAIL;
}

int create_is_aa_table(tld_strbuf* b)
{
        char buffer[1024];
        uint8_t arr[256];
                for(int i = 0; i < 256;i++){
                arr[i] = 0;
        }

        arr['A'] = 1;//	Ala	Alanine
        arr['C'] = 1;//	Cys	Cysteine
        arr['D'] = 1;//	Asp	Aspartic Acid
        arr['E'] = 1;//	Glu	Glutamic Acid
        arr['F'] = 1;//	Phe	Phenylalanine
        arr['G'] = 1;//	Gly	Glycine
        arr['H'] = 1;//	His	Histidine
        arr['I'] = 1;//	Ile	Isoleucine
        arr['K'] = 1;//	Lys	Lysine
        arr['L'] = 1;//	Leu	Leucine
        arr['M'] = 1;//	Met	Methionine
        arr['N'] = 1;//	Asn	Asparagine
        arr['P'] = 1;//	Pro	Proline
        arr['Q'] = 1;//	Gln	Glutamine
        arr['R'] = 1;//	Arg	Arginine
        arr['S'] = 1;//	Ser	Serine
        arr['T'] = 1;//	Thr	Threonine
        arr['V'] = 1;//	Val	Valine
        arr['W'] = 1;//	Trp	Tryptophan
        arr['Y'] = 1;//	Tyr	Tyrosine

        arr['X'] = 1;//	UNKNOWN

        arr['B'] = 1;//	UNKNOWN
        arr['J'] = 1;//	UNKNOWN
        arr['Z'] = 1;//	UNKNOWN
        arr['U'] = 1;//	UNKNOWN

        arr['a'] = 1;//	Ala	Alanine
        arr['c'] = 1;//	Cys	Cysteine
        arr['d'] = 1;//	Asp	Aspartic Acid
        arr['e'] = 1;//	Glu	Glutamic Acid
        arr['f'] = 1;//	Phe	Phenylalanine
        arr['g'] = 1;//	Gly	Glycine
        arr['h'] = 1;//	His	Histidine
        arr['i'] = 1;//	Ile	Isoleucine
        arr['k'] = 1;//	Lys	Lysine
        arr['l'] = 1;//	Leu	Leucine
        arr['m'] = 1;//	Met	Methionine
        arr['n'] = 1;//	Asn	Asparagine
        arr['p'] = 1;//	Pro	Proline
        arr['q'] = 1;//	Gln	Glutamine
        arr['r'] = 1;//	Arg	Arginine
        arr['s'] = 1;//	Ser	Serine
        arr['t'] = 1;//	Thr	Threonine
        arr['v'] = 1;//	Val	Valine
        arr['w'] = 1;//	Trp	Tryptophan
        arr['y'] = 1;//	Tyr	Tyrosine

        arr['x'] = 1;//	UNKNOWN

        arr['b'] = 1;//	UNKNOWN
        arr['j'] = 1;//	UNKNOWN
        arr['z'] = 1;//	UNKNOWN
        arr['u'] = 1;//	UNKNOWN

        RUN(tld_append(b, "const uint8_t is_aa[256] = {\n"));

        for(int i = 0; i < 256;i++){
                snprintf(buffer, 1024,"%3d,", arr[i]);
                RUN(tld_append(b,buffer));
                if(i != 0 && (i +1) % 16 == 0){
                        tld_append_char(b, '\n');
                }else  if(i != 0 && (i+1) %4 == 0){
                        tld_append_char(b, ' ');
                }
        }
        b->len--;
        RUN(tld_append(b, "\n};\n"));
        return OK;
ERROR:
        return FAIL;
}


int create_is_nuc_table(tld_strbuf* b)
{
        char buffer[1024];
        uint8_t arr[256];
        for(int i = 0; i < 256;i++){
                arr[i] = 0;
        }

        arr['A'] = 1;//	Adenine
        arr['C'] = 1;//	Cytosine
        arr['G'] = 1;//	Guanine
        arr['T'] = 1;// (or U)	Thymine (or Uracil)
        arr['R'] = 1;//	A or G
        arr['Y'] = 1;//	C or T
        arr['S'] = 1;//	G or C
        arr['W'] = 1;//	A or T
        arr['K'] = 1;//	G or T
        arr['M'] = 1;//	A or C
        arr['B'] = 1;//	C or G or T
        arr['D'] = 1;//	A or G or T
        arr['H'] = 1;//	A or C or T
        arr['V'] = 1;//	A or C or G
        arr['N'] = 1;//	any base

        arr['a'] = 1;//	Adenine
        arr['c'] = 1;//	Cytosine
        arr['g'] = 1;//	Guanine
        arr['t'] = 1;// (or U)	Thymine (or Uracil)
        arr['r'] = 1;//	A or G
        arr['y'] = 1;//	C or T
        arr['s'] = 1;//	G or C
        arr['w'] = 1;//	A or T
        arr['k'] = 1;//	G or T
        arr['m'] = 1;//	A or C
        arr['b'] = 1;//	C or G or T
        arr['d'] = 1;//	A or G or T
        arr['h'] = 1;//	A or C or T
        arr['v'] = 1;//	A or C or G
        arr['n'] = 1;//	any base


        RUN(tld_append(b, "const uint8_t is_nuc[256] = {\n"));

        for(int i = 0; i < 256;i++){
                snprintf(buffer, 1024,"%3d,", arr[i]);
                RUN(tld_append(b,buffer));
                if(i != 0 && (i +1) % 16 == 0){
                        tld_append_char(b, '\n');
                }else  if(i != 0 && (i+1) %4 == 0){
                        tld_append_char(b, ' ');
                }
        }
        b->len--;
        RUN(tld_append(b, "\n};\n"));
        return OK;
ERROR:
        return FAIL;
}

int create_rev_comp_table(tld_strbuf* b)
{
        char buffer[1024];
        uint8_t arr[256];
        for(int i = 0; i < 256;i++){
                arr[i] = i;
        }
        arr['A'] = 'T';
        arr['a'] = 't';

        arr['C'] = 'G';
        arr['c'] = 'g';

        arr['G'] = 'C';
        arr['g'] = 'c';

        arr['T'] = 'A';
        arr['t'] = 'a';

        RUN(tld_append(b, "const uint8_t comp_table[256] = {\n"));

        for(int i = 0; i < 256;i++){
                snprintf(buffer, 1024,"%3d,", arr[i]);
                RUN(tld_append(b,buffer));
                if(i != 0 && (i +1) % 16 == 0){
                        tld_append_char(b, '\n');
                }else  if(i != 0 && (i+1) %4 == 0){
                        tld_append_char(b, ' ');
                }
        }
        b->len--;
        RUN(tld_append(b, "\n};\n"));
        return OK;
ERROR:
        return FAIL;
}


