#ifndef MISC_H
#define MISC_H

#include "../core/tld-core.h"
#include "../string/str.h"
tld_external int tld_file_exists(const char* name);
tld_external int tld_dir_exists(const char *name);
tld_external int tld_dir_create(char *dir);
tld_external int tld_get_full_path(tld_strbuf **full, char *filename);
/* tld_external int make_cmd_line(char **command, int argc, char *const argv[]); */
tld_external int tld_capture_cmd_line(tld_strbuf **cmdline, const int argc, char *const argv[]);
tld_external int tld_get_filename(char* path, char** out);
tld_external int tld_get_dirname(char* path, char** out);

#endif
