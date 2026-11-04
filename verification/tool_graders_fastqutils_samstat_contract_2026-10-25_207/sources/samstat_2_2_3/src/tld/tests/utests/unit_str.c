#include "tld.h"
#include <stdio.h>


int main(void)
{
        char test[] = "Hello";
        char test2[] = "GIRAFFE";
        tld_strbuf* b = NULL;
        tld_strbuf_alloc(&b, 10);
        tld_append(b, test);
        LOG_MSG("LEN:%d", b->len);
        tld_append(b, test);
        LOG_MSG("LEN:%d", b->len);
        tld_append(b, test);
        LOG_MSG("LEN:%d", b->len);

        tld_append(b, test);
        LOG_MSG("LEN:%d", b->len);
        RUN(tld_append(b, test));
        LOG_MSG("LEN:%d", b->len);
        RUN(tld_prepend(b, test2));
        RUN(tld_append(b, test2));


        fprintf(stdout,"%s ; LEN:%d\n", TLD_STR(b), TLD_STRLEN(b));

        tld_strbuf_free(b);
        return EXIT_SUCCESS;
ERROR:
        return EXIT_FAILURE;
}
