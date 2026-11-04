#ifndef STR_H
#define STR_H

/* code here is inspired by the rayfork str code by Sas Luca */

#include "../core/tld-core.h"
#include <stdint.h>

typedef struct tld_string {
        uint8_t* str;
        int32_t len;
} tld_str;

typedef struct tld_string_buffer {
        uint8_t* str;
        int32_t len;
        int32_t alloc_len;
} tld_strbuf;

#define TLD_STR(X) ((char*)(X)->str)
#define TLD_STRLEN(X) (X)->len


tld_external int tld_strbuf_copy(tld_strbuf *t, tld_strbuf *s);
tld_external int tld_append(tld_strbuf *b, char *content);
tld_external int tld_append_char(tld_strbuf *b, char c);
tld_external int tld_prepend(tld_strbuf *b, char *content);

tld_external int tld_suffix_match(tld_str t, tld_str s);
tld_external int tld_prefix_match(tld_str t, tld_str s);

tld_external tld_str tld_strbuf_to_str(tld_strbuf s);
tld_external tld_str tld_char_to_str(char* s);

tld_external int tld_strmk(tld_str **string,const char *src);

tld_external int tld_strbuf_alloc(tld_strbuf **buffer, int size);
tld_external void tld_strbuf_free(tld_strbuf *b);

tld_external int tld_str_alloc(tld_str **string, int size);
tld_external void tld_str_free(tld_str *a);

#undef STR_IMPORT
#undef EXTERN


#endif
