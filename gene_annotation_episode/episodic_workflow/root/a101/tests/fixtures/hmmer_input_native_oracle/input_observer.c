/* Diagnostic observation only. Build/run only in root's bounded lifecycle.
 * Original esl_alphabet.c is separately compiled with its GuessAlphabet symbol
 * renamed to oracle_original_GuessAlphabet. Every classification below delegates
 * to that original function; this file supplies no classifier, parser, checksum,
 * weights, MAP algorithm, or scientific calculator.
 *
 * input_observer classifier COUNT_A ... COUNT_Z
 * input_observer guess FORMAT {auto|amino|DNA|RNA} ABSOLUTE_INPUT
 * input_observer read  FORMAT {auto|amino|DNA|RNA} ABSOLUTE_INPUT
 *
 * guess auto opens in text mode then calls the declared format's original
 * GuessAlphabet dispatcher without reading an MSA. read auto uses native digital
 * Open and its actual internal guessing. Native statuses are JSON data; a normal
 * diagnostic exits zero even when native open/read returns 3, 7, or 26.
 */
#include <esl_config.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "easel.h"
#include "esl_alphabet.h"
#include "esl_buffer.h"
#include "esl_msa.h"
#include "esl_msafile.h"

extern int oracle_original_GuessAlphabet(const int64_t *ct, int *ret_type);

typedef struct {
  int64_t counts[26];
  int status;
  int type;
  int64_t offset;
} ORACLE_CALL;
static ORACLE_CALL *calls = NULL;
static size_t ncalls = 0;
static ESL_MSAFILE *observed_afp = NULL;

int
esl_abc_GuessAlphabet(const int64_t *ct, int *ret_type)
{
  ORACLE_CALL *next;
  int status;
  int64_t offset = observed_afp ? (int64_t) esl_buffer_GetOffset(observed_afp->bf) : -1;
  status = oracle_original_GuessAlphabet(ct, ret_type);
  next = realloc(calls, (ncalls + 1) * sizeof(*calls));
  if (next == NULL) esl_fatal("observer allocation failed");
  calls = next;
  memcpy(calls[ncalls].counts, ct, sizeof(calls[ncalls].counts));
  calls[ncalls].status = status;
  calls[ncalls].type = *ret_type;
  calls[ncalls].offset = offset;
  ncalls++;
  return status;
}

static void
print_alphabet(int type)
{
  if      (type == eslAMINO) fputs("\"amino\"", stdout);
  else if (type == eslDNA)   fputs("\"DNA\"", stdout);
  else if (type == eslRNA)   fputs("\"RNA\"", stdout);
  else                      fputs("null", stdout);
}

static void
print_hex(const char *value)
{
  const unsigned char *p = (const unsigned char *) value;
  if (p == NULL) { fputs("null", stdout); return; }
  putchar('"');
  while (*p) printf("%02x", (unsigned int) *p++);
  putchar('"');
}

static void
print_hex_field(const char *key, const char *value)
{
  printf("\"%s\":", key);
  print_hex(value);
}

static void
print_calls(void)
{
  size_t i;
  int x;
  putchar('[');
  for (i = 0; i < ncalls; i++) {
    if (i) putchar(',');
    fputs("{\"counts_az\":[", stdout);
    for (x = 0; x < 26; x++) {
      if (x) putchar(',');
      printf("%" PRId64, calls[i].counts[x]);
    }
    printf("],\"status\":%d,\"alphabet\":", calls[i].status);
    print_alphabet(calls[i].type);
    fputs(",\"byte_offset\":", stdout);
    if (calls[i].offset < 0) fputs("null", stdout);
    else printf("%" PRId64, calls[i].offset);
    putchar('}');
  }
  putchar(']');
}

static int
alphabet_code(const char *name)
{
  if (!strcmp(name, "amino")) return eslAMINO;
  if (!strcmp(name, "DNA")) return eslDNA;
  if (!strcmp(name, "RNA")) return eslRNA;
  return eslUNKNOWN;
}

static int
parse_counts(char **argv, int64_t *ct)
{
  int i;
  int64_t total = 0;
  char *end;
  intmax_t value;
  const char *narrowed = "EFIJLOPQZACGDHKMRSVWY";
  for (i = 0; i < 26; i++) {
    errno = 0;
    end = NULL;
    value = strtoimax(argv[i], &end, 10);
    if (errno || end == argv[i] || *end || value < 0 || value > INT64_MAX) return 0;
    ct[i] = (int64_t) value;
    if (ct[i] > INT64_MAX - total) return 0;
    total += ct[i];
    if (strchr(narrowed, 'A' + i) && ct[i] > INT_MAX) return 0;
  }
  return 1;
}

static void
print_msa(const ESL_MSA *msa)
{
  int i, t;
  int64_t pos;
  uint32_t checksum;
  int checksum_status;
  if (msa == NULL) {
    fputs("\"nseq\":null,\"alen\":null,\"rows\":[],\"annotations\":null,"
          "\"metadata\":null,\"unparsed_gc\":[],\"unparsed_gr\":[],"
          "\"checksum_status\":null,\"native_checksum_uint32\":null", stdout);
    return;
  }
  if (!(msa->flags & eslMSA_DIGITAL) || !msa->abc)
    esl_fatal("observer requires an actual digital MSA");
  printf("\"nseq\":%d,\"alen\":%" PRId64 ",\"rows\":[", msa->nseq, msa->alen);
  for (i = 0; i < msa->nseq; i++) {
    if (i) putchar(',');
    printf("{\"ordinal\":%d,", i);
    print_hex_field("name_hex", msa->sqname[i]);
    fputs(",\"digital\":\"", stdout);
    for (pos = 1; pos <= msa->alen; pos++) {
      if (msa->ax[i][pos] >= msa->abc->Kp) esl_fatal("unexpected digital symbol");
      putchar(msa->abc->sym[msa->ax[i][pos]]);
    }
    fputs("\",", stdout);
    print_hex_field("description_hex", msa->sqdesc ? msa->sqdesc[i] : NULL); putchar(',');
    print_hex_field("accession_hex", msa->sqacc ? msa->sqacc[i] : NULL); putchar(',');
    print_hex_field("SS_hex", msa->ss ? msa->ss[i] : NULL); putchar(',');
    print_hex_field("SA_hex", msa->sa ? msa->sa[i] : NULL); putchar(',');
    print_hex_field("PP_hex", msa->pp ? msa->pp[i] : NULL);
    putchar('}');
  }
  fputs("],\"annotations\":{", stdout);
  print_hex_field("RF_hex", msa->rf); putchar(',');
  print_hex_field("MM_hex", msa->mm); putchar(',');
  print_hex_field("SS_cons_hex", msa->ss_cons); putchar(',');
  print_hex_field("SA_cons_hex", msa->sa_cons); putchar(',');
  print_hex_field("PP_cons_hex", msa->pp_cons);
  fputs("},\"metadata\":{", stdout);
  print_hex_field("name_hex", msa->name); putchar(',');
  print_hex_field("accession_hex", msa->acc); putchar(',');
  print_hex_field("description_hex", msa->desc); putchar(',');
  print_hex_field("author_hex", msa->au);
  fputs("},\"unparsed_gc\":[", stdout);
  for (t = 0; t < msa->ngc; t++) {
    if (t) putchar(',');
    putchar('{'); print_hex_field("tag_hex", msa->gc_tag[t]); putchar(',');
    print_hex_field("value_hex", msa->gc[t]); putchar('}');
  }
  fputs("],\"unparsed_gr\":[", stdout);
  for (t = 0; t < msa->ngr; t++) {
    if (t) putchar(',');
    putchar('{'); print_hex_field("tag_hex", msa->gr_tag[t]);
    fputs(",\"row_values_hex\":[", stdout);
    for (i = 0; i < msa->nseq; i++) {
      if (i) putchar(',');
      print_hex(msa->gr[t][i]);
    }
    fputs("]}", stdout);
  }
  checksum_status = esl_msa_Checksum(msa, &checksum);
  printf("],\"checksum_status\":%d,\"native_checksum_uint32\":", checksum_status);
  if (checksum_status == eslOK) printf("%" PRIu32, checksum);
  else fputs("null", stdout);
}

int
main(int argc, char **argv)
{
  ESL_ALPHABET *abc = NULL;
  ESL_MSAFILE *afp = NULL;
  ESL_MSA *msa = NULL;
  int64_t ct[26];
  int type = eslUNKNOWN;
  int status, open_status = -1, read_status = -1;
  int format = eslMSAFILE_UNKNOWN;
  int requested = eslUNKNOWN;
  int classifier, guess;
  const char *mode;
  if (argc < 2) return 2;
  mode = argv[1];
  classifier = !strcmp(mode, "classifier");
  guess = !strcmp(mode, "guess");
  if (classifier) {
    if (argc != 28 || !parse_counts(argv + 2, ct)) return 2;
    status = esl_abc_GuessAlphabet(ct, &type);
  } else {
    if (argc != 5 || (!guess && strcmp(mode, "read"))) return 2;
    format = esl_msafile_EncodeFormat(argv[2]);
    if (format == eslMSAFILE_UNKNOWN || argv[4][0] != '/') return 2;
    requested = alphabet_code(argv[3]);
    if (requested == eslUNKNOWN && strcmp(argv[3], "auto")) return 2;
    if (requested != eslUNKNOWN && (abc = esl_alphabet_Create(requested)) == NULL) return 2;
    /* text-open for direct guessing only: no MSA parsing occurs in guess mode */
    open_status = esl_msafile_Open(guess && !abc ? NULL : &abc, argv[4], NULL, format, NULL, &afp);
    status = open_status;
    if (open_status == eslOK) {
      if (guess && !abc) {
        observed_afp = afp;
        status = esl_msafile_GuessAlphabet(afp, &type);
        observed_afp = NULL;
      } else {
        type = abc->type;
        if (!guess) {
          read_status = esl_msafile_Read(afp, &msa);
          status = read_status;
        }
      }
    }
  }
  printf("{\"kind\":\"diagnostic_easel_alignment_input\",\"version\":1,"
         "\"easel_version\":\"%s\",\"mode\":\"%s\",\"format\":", EASEL_VERSION, mode);
  if (classifier) fputs("null", stdout); else printf("\"%s\"", argv[2]);
  fputs(",\"requested_alphabet\":", stdout);
  if (classifier) fputs("null", stdout); else printf("\"%s\"", argv[3]);
  printf(",\"status\":%d,\"open_status\":", status);
  if (open_status < 0) fputs("null", stdout); else printf("%d", open_status);
  fputs(",\"read_status\":", stdout);
  if (read_status < 0) fputs("null", stdout); else printf("%d", read_status);
  fputs(",\"selected_alphabet\":", stdout); print_alphabet(type);
  fputs(",\"classifier_calls\":", stdout); print_calls();
  fputs(",\"error_hex\":", stdout); print_hex(afp ? afp->errmsg : NULL);
  fputs(",\"read_line_number\":", stdout);
  if (afp && read_status >= 0) printf("%" PRId64, afp->linenumber); else fputs("null", stdout);
  putchar(','); print_msa(msa); fputs("}\n", stdout);
  if (msa) esl_msa_Destroy(msa);
  if (afp) esl_msafile_Close(afp);
  if (abc) esl_alphabet_Destroy(abc);
  free(calls);
  return 0;
}
