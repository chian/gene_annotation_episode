/* Diagnostic only: direct retained Easel RNG/Deal calls, not an alimask CLI.
 * Compile/run only through the root-owned bounded native lifecycle. Link the
 * pinned esl_rand64.c itself, with libeasel supplying its support functions.
 * This authoring packet has not compiled or executed this source.
 *
 * Usage: sampler_oracle deal POPULATION SAMPLE SEED
 *        sampler_oracle stream SEED COUNT
 */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "easel.h"
#include "esl_rand64.h"

static int
positive_u64(const char *text, uint64_t *out)
{
  const char *p;
  char *end;
  unsigned long long parsed;
  if (!text || !*text) return 0;
  for (p = text; *p; p++) if (*p < '0' || *p > '9') return 0;
  errno = 0;
  parsed = strtoull(text, &end, 10);
  if (errno || *end || parsed == 0 || parsed > UINT64_MAX) return 0;
  *out = (uint64_t) parsed;
  return 1;
}

int
main(int argc, char **argv)
{
  ESL_RAND64 *rng;
  uint64_t seed, count, n, m;
  int64_t *deal;
  uint64_t i;

  if (argc == 4 && strcmp(argv[1], "stream") == 0)
    {
      if (!positive_u64(argv[2], &seed) || !positive_u64(argv[3], &count)) return 2;
      rng = esl_rand64_Create(seed);
      if (!rng) return 3;
      printf("{\"kind\":\"diagnostic_easel_rand64\",\"seed\":%" PRIu64 ",\"words\":[", seed);
      for (i = 0; i < count; i++)
        printf("%s%" PRIu64, (i ? "," : ""), esl_rand64(rng));
      printf("]}\n");
      esl_rand64_Destroy(rng);
      return 0;
    }

  if (argc != 5 || strcmp(argv[1], "deal") != 0) return 2;
  if (!positive_u64(argv[2], &n) || !positive_u64(argv[3], &m) ||
      !positive_u64(argv[4], &seed) || n > INT64_MAX || m > n ||
      m > INT64_MAX / 13 || m > SIZE_MAX / sizeof(int64_t)) return 2;
  deal = malloc(sizeof(int64_t) * (size_t) m);
  if (!deal) return 3;
  rng = esl_rand64_Create(seed);
  if (!rng) { free(deal); return 3; }
  if (esl_rand64_Deal(rng, (int64_t) m, (int64_t) n, deal) != eslOK)
    { esl_rand64_Destroy(rng); free(deal); return 4; }

  printf("{\"kind\":\"diagnostic_easel_rand64_Deal\",\"population_size\":%" PRIu64
         ",\"sample_size\":%" PRIu64 ",\"seed\":%" PRIu64 ",\"rows\":[", n, m, seed);
  for (i = 0; i < m; i++) printf("%s%" PRId64, (i ? "," : ""), deal[i]);
  printf("]}\n");
  esl_rand64_Destroy(rng);
  free(deal);
  return 0;
}
