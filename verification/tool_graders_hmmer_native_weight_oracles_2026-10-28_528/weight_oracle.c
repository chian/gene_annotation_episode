/* Diagnostic only; build/run inside the root-owned bounded verification job.
 *
 * This translation unit includes the unmodified retained esl_msaweight.c.
 * Its DNorm call is intercepted only to COPY the incoming raw vector, then
 * immediately delegates to the original native DNorm. DScale is untouched.
 * No weighting, identity, tree, cluster, or normalization algorithm is copied.
 * Independent native calls expose the actual UPGMA tree / cluster arrays.
 * Hexadecimal double strings preserve every double bit in the JSON output.
 * This program is not alimask and its output is not an original CLI artifact.
 *
 * Usage: weight_oracle gsc ALPHABET INPUT.sto
 *        weight_oracle blosum ALPHABET INPUT.sto CUTOFF
 *        weight_oracle normalize NONNEGATIVE_WEIGHT [...]
 * ALPHABET is one of dna, rna, amino; native input is explicit Stockholm.
 */
#include <esl_config.h>

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "easel.h"
#include "esl_alphabet.h"
#include "esl_distance.h"
#include "esl_dmatrix.h"
#include "esl_msa.h"
#include "esl_msacluster.h"
#include "esl_msafile.h"
#include "esl_tree.h"
#include "esl_vectorops.h"  /* Original prototypes must precede interception. */

#if defined(eslMSAWEIGHT_REGRESSION) || defined(eslMSACLUSTER_REGRESSION)
#error "The oracle requires the retained non-regression digital algorithms"
#endif

static double *oracle_raw = NULL;
static int64_t oracle_count = 0;
static int oracle_norm_calls = 0;

static void
oracle_capture_DNorm(double *vec, int64_t n)
{
  if (oracle_raw == NULL || n != oracle_count || oracle_norm_calls != 0)
    esl_fatal("unexpected normalization interception");
  memcpy(oracle_raw, vec, sizeof(double) * (size_t) n);
  oracle_norm_calls++;
  esl_vec_DNorm(vec, n);
}

#define esl_vec_DNorm oracle_capture_DNorm
#include "esl_msaweight.c"
#undef esl_vec_DNorm

static void
oracle_require_ok(int status, const char *operation)
{
  if (status != eslOK) esl_fatal("%s returned %d", operation, status);
}

static int
oracle_nonnegative_double(const char *text, double *value)
{
  char *end = NULL;
  errno = 0;
  *value = strtod(text, &end);
  return text[0] != '\0' && end != text && *end == '\0' && errno == 0
         && isfinite(*value) && *value >= 0.0;
}

static void
oracle_double_array(const double *vec, int64_t n)
{
  int64_t i;
  putchar('[');
  for (i = 0; i < n; i++) printf("%s\"%a\"", i ? "," : "", vec[i]);
  putchar(']');
}

static void
oracle_int_array(const int *vec, int n)
{
  int i;
  putchar('[');
  for (i = 0; i < n; i++) printf("%s%d", i ? "," : "", vec[i]);
  putchar(']');
}

static void
oracle_print_vectors(const double *raw, const double *normalized, int64_t n)
{
  printf("\"raw_weights_hex\":");
  oracle_double_array(raw, n);
  printf(",\"normalized_weights_hex\":");
  oracle_double_array(normalized, n);
  printf(",\"normalization_sum_hex\":\"%a\"", esl_vec_DSum(raw, n));
}

static int
oracle_normalize(int argc, char **argv)
{
  int i, n = argc - 2;
  double *raw = NULL, *weights = NULL;
  if (n < 1) return 2;
  raw = malloc(sizeof(double) * (size_t) n);
  weights = malloc(sizeof(double) * (size_t) n);
  if (raw == NULL || weights == NULL) esl_fatal("normalization allocation failed");
  for (i = 0; i < n; i++)
    if (!oracle_nonnegative_double(argv[i + 2], &raw[i]))
      { free(raw); free(weights); return 2; }
  memcpy(weights, raw, sizeof(double) * (size_t) n);
  esl_vec_DNorm(weights, n);
  esl_vec_DScale(weights, n, (double) n);
  printf("{\"kind\":\"diagnostic_easel_vector_normalization\","
         "\"easel_version\":\"%s\",\"sequence_count\":%d,", EASEL_VERSION, n);
  oracle_print_vectors(raw, weights, n);
  printf("}\n");
  free(weights);
  free(raw);
  return 0;
}

int
main(int argc, char **argv)
{
  ESL_ALPHABET *abc = NULL;
  ESL_MSAFILE *afp = NULL;
  ESL_MSA *msa = NULL;
  ESL_DMATRIX *distance = NULL;
  ESL_TREE *tree = NULL;
  int *assignment = NULL, *sizes = NULL;
  int alphabet, is_gsc, nclusters = 0, i, j, first_pair = 1;
  int64_t column;
  double cutoff = 0.0;

  if (argc >= 2 && strcmp(argv[1], "normalize") == 0)
    return oracle_normalize(argc, argv);
  if (argc < 4) return 2;
  is_gsc = strcmp(argv[1], "gsc") == 0;
  if (!is_gsc && strcmp(argv[1], "blosum") != 0) return 2;
  if (is_gsc ? argc != 4 : argc != 5) return 2;
  if (!is_gsc && (!oracle_nonnegative_double(argv[4], &cutoff) || cutoff > 1.0)) return 2;
  if      (strcmp(argv[2], "dna")   == 0) alphabet = eslDNA;
  else if (strcmp(argv[2], "rna")   == 0) alphabet = eslRNA;
  else if (strcmp(argv[2], "amino") == 0) alphabet = eslAMINO;
  else return 2;

  abc = esl_alphabet_Create(alphabet);
  if (abc == NULL) esl_fatal("alphabet allocation failed");
  oracle_require_ok(esl_msafile_Open(&abc, argv[3], NULL, eslMSAFILE_STOCKHOLM, NULL, &afp),
                    "esl_msafile_Open");
  oracle_require_ok(esl_msafile_Read(afp, &msa), "esl_msafile_Read");
  if (!(msa->flags & eslMSA_DIGITAL) || msa->nseq < 1 || msa->alen < 1)
    esl_fatal("oracle requires a nonempty digital alignment");
  oracle_count = msa->nseq;
  oracle_raw = malloc(sizeof(double) * (size_t) oracle_count);
  if (oracle_raw == NULL) esl_fatal("raw weight allocation failed");
  if (is_gsc) oracle_require_ok(esl_msaweight_GSC(msa), "esl_msaweight_GSC");
  else        oracle_require_ok(esl_msaweight_BLOSUM(msa, cutoff), "esl_msaweight_BLOSUM");
  /* Native singleton weighting returns 1 before normalization/tree building. */
  if (msa->nseq == 1) oracle_raw[0] = msa->wgt[0];
  if (oracle_norm_calls != (msa->nseq == 1 ? 0 : 1))
    esl_fatal("native normalization call count changed");

  if (is_gsc && msa->nseq > 1)
    {
      oracle_require_ok(esl_dst_XDiffMx(abc, msa->ax, msa->nseq, &distance), "esl_dst_XDiffMx");
      oracle_require_ok(esl_tree_UPGMA(distance, &tree), "esl_tree_UPGMA");
      oracle_require_ok(esl_tree_SetCladesizes(tree), "esl_tree_SetCladesizes");
    }
  if (!is_gsc)
    oracle_require_ok(esl_msacluster_SingleLinkage(msa, cutoff, &assignment, &sizes, &nclusters),
                      "esl_msacluster_SingleLinkage");

  printf("{\"kind\":\"diagnostic_easel_msaweight\",\"easel_version\":\"%s\","
         "\"method\":\"%s\",\"alphabet\":\"%s\",\"sequence_count\":%d,"
         "\"alignment_width\":%" PRId64 ",\"normalization_calls\":%d,",
         EASEL_VERSION, argv[1], argv[2], msa->nseq, msa->alen, oracle_norm_calls);
  oracle_print_vectors(oracle_raw, msa->wgt, msa->nseq);
  printf(",\"raw_basis\":\"%s\",\"digitized_sequences\":[",
         msa->nseq == 1 ? "native_singleton_early_return" : "copy_before_original_DNorm");
  for (i = 0; i < msa->nseq; i++)
    {
      printf("%s\"", i ? "," : "");
      for (column = 1; column <= msa->alen; column++) putchar(abc->sym[msa->ax[i][column]]);
      putchar('"');
    }
  printf("],\"pairs\":[");
  for (i = 0; i < msa->nseq; i++)
    for (j = i + 1; j < msa->nseq; j++)
      {
        double identity;
        int nid, denominator;
        oracle_require_ok(esl_dst_XPairId(abc, msa->ax[i], msa->ax[j], &identity, &nid, &denominator),
                          "esl_dst_XPairId");
        printf("%s{\"rows\":[%d,%d],\"identity_hex\":\"%a\","
               "\"identical_residues\":%d,\"denominator\":%d}",
               first_pair ? "" : ",", i, j, identity, nid, denominator);
        first_pair = 0;
      }
  printf("],\"tree\":");
  if (!is_gsc) printf("null,\"tree_basis\":null");
  else
    {
      int nodes = tree == NULL ? 0 : tree->N - 1;
      printf("{\"children\":[");
      for (i = 0; i < nodes; i++)
        printf("%s[%d,%d]", i ? "," : "", tree->left[i], tree->right[i]);
      printf("],\"branches_hex\":[");
      for (i = 0; i < nodes; i++)
        printf("%s[\"%a\",\"%a\"]", i ? "," : "", tree->ld[i], tree->rd[i]);
      printf("],\"clade_sizes\":");
      oracle_int_array(tree == NULL ? NULL : tree->cladesize, nodes);
      printf("},\"tree_basis\":\"%s\"", tree == NULL
             ? "singleton_early_return_no_native_tree" : "independent_esl_tree_UPGMA");
    }
  printf(",\"clusters\":");
  if (is_gsc) printf("null,\"clusters_basis\":null");
  else
    {
      printf("{\"assignment\":");
      oracle_int_array(assignment, msa->nseq);
      printf(",\"sizes\":");
      oracle_int_array(sizes, nclusters);
      printf(",\"identity_cutoff_hex\":\"%a\"},"
             "\"clusters_basis\":\"independent_esl_msacluster_SingleLinkage\"", cutoff);
    }
  printf("}\n");

  free(assignment);
  free(sizes);
  free(oracle_raw);
  if (tree != NULL) esl_tree_Destroy(tree);
  if (distance != NULL) esl_dmatrix_Destroy(distance);
  esl_msa_Destroy(msa);
  esl_msafile_Close(afp);
  esl_alphabet_Destroy(abc);
  return 0;
}
