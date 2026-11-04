#ifndef TLD_RNG_H
#define TLD_RNG_H


#include "../core/tld-core.h"

typedef struct rng_state rng_state;
struct rng_dist;

tld_external int init_rng(struct rng_state **rng, uint64_t seed);
tld_external int tld_rng_set_seed(struct rng_state *s, uint64_t seed);
tld_external int init_rng_from_rng(struct rng_state** target, struct rng_state* rng);
tld_external int tl_random_sdist_init(struct rng_dist** rng_dist,double* w, int n,int seed);
tld_external int tl_random_sdist_smpl(struct rng_dist* d);
tld_external void tl_random_sdist_free(struct rng_dist* d);

tld_external void free_rng(struct rng_state* rng);

tld_external double tl_random_double(struct rng_state* rng);
tld_external double tl_random_gaussian(struct rng_state* rng, double mu, double sigma);
tld_external double tl_random_gamma(struct rng_state* rng, double shape, double scale);
tld_external int tl_random_int(struct rng_state* rng,int a);



#endif
