# Pure Easel PB row sampler — authoring packet 525

Status: helper and tests authored; test execution, native conformance, shared
reconstruction integration and episode verification remain unverified here.
No inventory completion claim is made. The original user attachment remains
authoritative. No GOAL.md or replacement goal/scope file was read or written.

The two assigned production/test paths were absent at the first source scan.
`BEFORE.json` records that observation. Only those two new paths and this
evidence directory are owned by this packet. The shared calculator, parser,
driver, worker, views, prompts, library, literature graders and W05 are untouched
by this author.

The helper implements
`sample_easel_pb_rows(population_size, *, sample_size, seed) -> list[int]`.
Returned integers are sorted, unique, zero-based source-row ordinals. Their
meaning is deterministic reconstruction from explicit sampler inputs, not
native stdout records. They carry no score, probability or confidence meaning.

The implementation ports the retained 312-word MT19937-64 generator and
`esl_rand64_Deal`'s Vitter D/A draw sequence and operation order. It includes the
initial half-open Vprime draw even for immediate A or a single sample, native
uint64 seed overflow, open versus half-open double conversion, C log(0), and
C round()'s nonnegative half-away behavior. It does not use Python random.

The root reviewed the following source-based domain clarification before it was
coded: all arguments must be built-in integers excluding bool; population and
sample are positive signed-int64 values; sample <= population and
sample <= INT64_MAX // 13; seed is 1..UINT64_MAX. Invalid settings raise exactly
`ValueError('settings_invalid')`. The 13*m bound excludes undefined native signed
overflow, rather than imposing a resource policy. Native m=0 still writes an
output element, so it cannot supply the port's requested zero-length result.
Native seed 0 chooses time/process state. Neither is silently reinterpreted.
The unused native initialization of 1/(m-1) for m=1 is not evaluated as a Python
division; its first used value is calculated in the m>1 D branch.

The common integration retains ownership of N>50000 eligibility, sample size
10000, retained-profile effective PB seed 42, unknown original provenance,
fragment rejection above 5000, consensus fallbacks, PB counts/weights,
normalization and occurrence-key joins. No CLI-seed inference occurs here.

Complete native source read: `esl_rand64.c` (843 lines), `esl_rand64.h` (32),
`esl_msaweight.c` (1874), `esl_msaweight.h` (81), all under the retained
Infernal 1.1.5 Easel tree. These cover the entire sampler and its direct PB caller
and configuration. The complete 581-line 516 contract was read and reread after
the source examination. The authoritative objective and all ten operating
principles were reread verbatim from the attachment. The source pin manifest
records actual bytes, not an assertion about an executable's build history.

Hand-traced scripted-draw examples in the tests (not native captures):

| Population / sample | Draws, in order | Expected reconstructed row ordinals |
| --- | --- | --- |
| 10 / 3, immediate A | half .25; open .5; open .5; half .4 | [1, 4, 7] |
| 100 / 2, D then single | half .25; open .25 | [50, 63] |
| 100 / 3, D then A | half .016; open .5; open .5; half .25 | [74, 82, 87] |
| 100 / 2, unusable initial skip | half 0; open .25; open .25 | [50, 63] |
| 100 / 2, rejected proposal | half .25; open .99; open .25; open .25 | [50, 63] |
| 100 / 3, second acceptance | half .13; open .96; open .25; open .25 | [49, 75, 82] |

Additional authored tests cover full samples, m=1 and large int64 population
conversion, seed recurrence overflow, floating endpoints/rounding, strict bad
types/ranges and validation before RNG allocation. PB-scale N=50001, 130000 and
130001 with m=10000 checks exercise immediate A, the strict switch boundary,
and D followed by A, plus increasing order, bounds, repeatability and seed
differences. Native numerical agreement is not established by these properties.

`sampler_oracle.c` is an optional direct Easel diagnostic for root-owned lifecycle
verification. It can emit a generator word stream or full Deal index array.
It is not an original alimask CLI measurement, does not sample an MSA, and is
not part of production grading. Compile by linking the pinned `esl_rand64.c`
itself, the retained Easel support library and libm, retaining source/compiler/
binary identity in the lifecycle receipt. Intended comparisons include seed
1, 42 and UINT64_MAX; at least 625 words to span two state refills; small and
full samples; N=50001/m=10000 and N=130001/m=10000 with seed42 and seed43.

Only standard-library source inspection, editing, hashing, diff generation and
AST parsing were performed here. The host command `python` was unavailable;
subsequent permitted source operations used `python3`. No application or
scientific module was imported, no pytest collection or execution occurred,
and no native program, compiler, network access or job was launched.

Exact test target for root's frozen verification:
`tests/test_hmmer_alignment_pb_sampling.py`.
`AST_CHECK.json` lists individual selectors from the unexecuted test source.
`FROZEN_MANIFEST.json` and `OWNED_DIFF.patch` identify the handed-off bytes.
Platform/libm conformance and full requested-return paths remain root-owned
verification requirements.
