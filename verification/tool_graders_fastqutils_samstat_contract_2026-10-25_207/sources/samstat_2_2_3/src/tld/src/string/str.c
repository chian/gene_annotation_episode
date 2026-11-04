#include "str.h"

#include "../core/tld-core.h"
#include "../alloc/tld-alloc.h"
#include <stdint.h>
#include <string.h>

tld_internal inline int tld_strbuf_free_space(tld_strbuf *b);

tld_internal int tld_strbuf_resize(tld_strbuf *b, int new_size);

int tld_strbuf_alloc(tld_strbuf **buffer, int size)
{
        tld_strbuf* b = NULL;
        MMALLOC(b,sizeof(tld_strbuf));
        if(size == 0){
                size = 1024;
        }
        b->alloc_len = size;
        b->len = 0;
        b->str = NULL;
        galloc(&b->str, b->alloc_len);

        *buffer = b;
        return OK;
ERROR:
        return FAIL;
}

void tld_strbuf_free(tld_strbuf *b)
{
        if(b){
                if(b->str){
                        gfree(b->str);
                }
                MFREE(b);
        }
}

int tld_strbuf_resize(tld_strbuf *b, int new_size)
{
        uint8_t* tmp = NULL;
        if (new_size > b->alloc_len){
                galloc(&tmp , new_size);

                memcpy(tmp,b->str,b->len);
                tmp[b->len] = 0;

                gfree(b->str);
                b->str = tmp;
        }
        return OK;
ERROR:
        if(tmp){
                gfree(tmp);
        }
        return FAIL;
}

inline int tld_strbuf_free_space(tld_strbuf *b)
{
        int space = b->alloc_len - b->len;
        return space;
}

int tld_strbuf_ensure_size(tld_strbuf *b, int size)
{
        int space = tld_strbuf_free_space(b);
        if(space <= size){
                int new_size = MACRO_MAX(b->alloc_len*2, b->alloc_len + (size - space) + 1);
                RUN(tld_strbuf_resize(b, new_size));
        }
        return OK;
ERROR:
        return FAIL;
}

int tld_strbuf_copy(tld_strbuf *t, tld_strbuf *s)
{
        /* tld_strbuf_ensure_size(t, s->len); */
        RUN(tld_strbuf_ensure_size(t,s->len));

        memcpy(t->str, s->str, s->len);
        t->len = s->len;
        t->str[t->len] = 0;
        return OK;
ERROR:
        return FAIL;
}


int tld_prepend(tld_strbuf *b, char *content)
{
        int size = strlen(content);

        RUN(tld_strbuf_ensure_size(b, size));
        memmove(b->str + size, b->str, b->len);
        memcpy(b->str, content, size);
        b->len += size;
        b->str[b->len] = 0;
        return OK;
ERROR:
        return FAIL;
}

int tld_append(tld_strbuf *b, char *content)
{
        int size = strlen(content);

        RUN(tld_strbuf_ensure_size(b, size));

        memcpy(b->str+b->len,content, size);
        b->len += size;
        b->str[b->len] = 0;

        return OK;
ERROR:
        return FAIL;
}

int tld_append_char(tld_strbuf *b, char c)
{
        /* int size = 1; */
        RUN(tld_strbuf_ensure_size(b, 1));
        /* memcpy(b->str+b->len,content, size); */
        b->str[b->len] = c;
        b->len++;
        b->str[b->len] = 0;

        return OK;
ERROR:
        return FAIL;
}

int tld_suffix_match(tld_str t, tld_str s)
{

        if (t.len < s.len) return 0;
        int offset = t.len - s.len;
        int cmp = memcmp(t.str + offset, s.str, s.len);
        return cmp == 0;
}

int tld_prefix_match(tld_str t, tld_str s)
{
        if (t.len < s.len) return 0;
        int cmp = memcmp(t.str, s.str, s.len);
        return cmp == 0;
}

tld_str tld_strbuf_to_str(tld_strbuf s)
{
    tld_str r = {0};
    r.str = s.str;
    r.len = s.len;
    return r;
}

tld_str tld_char_to_str(char* s)
{
        int size = strlen(s);
        tld_str r = {
                .str = (uint8_t*) s,
                .len = size,
        };
        return r;
}


int tld_strmk(tld_str **string,const char *src)
{
        int size = strlen(src);
        tld_str* a = NULL;
        size = size +1;
        RUN(tld_str_alloc(&a,size));
        memcpy(a->str,src, size);
        a->str[size] = 0;

        *string = a;
        return OK;
ERROR:
        return FAIL;
}

int tld_str_alloc(tld_str **string, int size)
{
        tld_str* a = NULL;
        MMALLOC(a, sizeof(tld_str));
        a->len = size;
        a->str = NULL;
        galloc(&a->str, a->len);
        *string = a;
        return OK;
ERROR:
        tld_str_free(a);
        return FAIL;
}

void tld_str_free(tld_str *a)
{
        if(a){
                if(a->str){
                        gfree(a->str);
                }
                MFREE(a);
        }
}
