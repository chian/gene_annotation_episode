# Unexecuted native conformance recipes

This file records proposed bounded verification, not completed execution. No
compiler, HMMER command or diagnostic was run while authoring packet 526.
Root owns execution through the existing `native_lifecycle`: 20 GiB RAM,
4 GiB scratch, zero swap, no invented wall-time cap. Preserve actual handles,
source/compiler/executable/library hashes, argv, original input bytes, stdout,
stderr and lifecycle receipts. Diagnostic output is distinct from original
alimask CLI measurements and must never be inserted into production grading.

The exact retained support tree is
`resources/software/infernal-1.1.5/`, relative to the repository. The selected
original executable is `hmmer/src/alimask`, SHA256
`4cf273b7b4b52363468b758a39bedf8f00540b01983bf6641ffd36140afad547`.
Compilation support is `hmmer/src/{p7_config.h,hmmer.h,libhmmer.a}` and
`easel/{esl_config.h,libeasel.a}`, with their included headers. Preserve the
source subtree/include hierarchy; do not infer a profile from a new executable.
`SOURCE_MANIFEST.json` records the inspected source/static-library identities.

`native_map_oracle.c` includes the original `hmmer/src/alimask.c` translation
unit with its CLI `main` renamed. It uses the native option table and
`p7_Alimask_MakeModel2AliMap`, calls native GSC/BLOSUM/PB and fragment marking,
and emits normalized weights, PB diagnostic columns/flags, marked digital rows,
and the full map. This is a source-linked diagnostic, not a replacement tool.
A bounded compiler invocation can use this argument structure, with root's
frozen checkout and lifecycle scratch paths substituted explicitly:

```text
cc -O2 -std=c99
   -I<FROZEN>/resources/software/infernal-1.1.5/hmmer/src
   -I<FROZEN>/resources/software/infernal-1.1.5/easel
   <FROZEN>/verification/tool_graders_hmmer_map_integration_2026-10-28_526/native_map_oracle.c
   <FROZEN>/resources/software/infernal-1.1.5/hmmer/src/libhmmer.a
   <FROZEN>/resources/software/infernal-1.1.5/easel/libeasel.a
   -lm -lpthread -o <BOUNDED_SCRATCH>/native_map_oracle
```

Invocation accepts the original option syntax, e.g. `--dna --wgsc --fast
--symfrac .6 --fragthresh 0 --model2ali 1-1 --informat stockholm <input.sto>`.
The diagnostic prints the complete map, independently of that range selection.
CLI conformance should separately request each singleton model position
(maximum 100 intervals), or safe alignment interval `1-4`, through the actual
selected `alimask` executable. Never request after-last-match native ali2model
ranges or substitute a successful diagnostic for a rejected native command.

Recommended missing native cases are small GSC/BLOSUM examples with ties,
identical rows, degenerates and cutoff equality; and PB short-column inputs at
50,000, 50,001 and 130,001 rows. Repeat PB CLI seed 0, 42 and 17 while verifying
that the source-linked internal PB seed remains 42 for this retained profile.
The 525 sampler diagnostic and 528 raw-weight conformance packet have separate
owners and should be reused for their direct helper comparisons.

The common integration's three new child-path cases are already authored in
`tests/test_hmmer_alignment_map_episode_path.py`. GSC/BLOSUM use
`AAAA,AAAA,C--C`, final symfrac .6/fragthresh 0. The synthetic source-defined
expected raw weights are `.25,.25,.5` / `.5,.5,1`; both normalize to
`.75,.75,1.5` and yield map `[1,4]`. PB uses 50,001 rows: 10,000 `A--A`, then
40,001 `CCCC`, final symfrac .65/fragthresh 0, selected CLI seed 17. These
expected values are hypotheses to verify against real native output, not
native evidence merely because tests contain them.

The forced-sample fragment/fallback tests in
`tests/test_hmmer_alignment_map_context.py` deliberately isolate integration
semantics. They are not sampler conformance. For additional authentic PB
boundary diagnostics, construct input row positions from the separately
verified native sample indices, placing exactly 5,000 or 5,001 `--A-` fragments
inside that sample. Alternating `A--A` and `-AA-` in sampled rows produces no
sample consensus at the strict .5 gap boundary; remaining `AAAA` rows exercise
all-row fallback. An even full population of the alternating pair exercises
all-column fallback. Preserve all input bytes and identities.

Reusing old evidence does not require another native call. The retained 277
alignment-to-model publication used by the legacy regression is:

`verification/tool_graders_hmmer_preparation_workflow_2026-10-26_277/check009/temporary/test_all_native_modes_through_3/`

Stage its complete `state/` and nested
`run/.../grading/native-hmmer-preparation-grading/prepared.json` and
`run/.../projection/native-hmmer-preparation-projection/` receipt tree. The test
copies state/projection into temporary storage and opens only the copies. It
checks prepared-file SHA256
`85824c53c759e26aacebed9d8ad295578f3fbf3b9b208ee985d633678441652c`
and publication-file SHA256
`43ce501621049bc2c2c3b838fb958fab91a0b1acaa835eb6ff53d9d9714d94b0`.
Original numerical artifacts remain unchanged and context remains absent.

Test imports/support also require the retained 259, 267 and 270 fixture
packages under `verification/`, plus the existing test helper modules. Full
pure retained-regression modules can additionally require the 269 and 271
fixtures they already name. Do not rerun the old native fixture-generating
tests to satisfy these dependencies. `UNEXECUTED_TESTS.json` distinguishes
pure/retained checks, new bounded workers, and three new native episode cases.
