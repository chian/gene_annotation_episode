#include "tld.h"
#include <stdio.h>



int main(int argc, char *argv[])
{

        tld_strbuf* cmd = NULL;

        RUN(tld_capture_cmd_line(&cmd, argc,argv));

        LOG_MSG("%s", TLD_STR(cmd));

        tld_strbuf_free(cmd);

        return EXIT_SUCCESS;
ERROR:
        if(cmd){
                tld_strbuf_free(cmd);
        }
        return EXIT_FAILURE;
}
