# Root-owned native verification recipe — authored, not executed

Run the selected test through the frozen `native_lifecycle` / `local_jobs`
verification path. All application imports, pytest collection/execution,
compiler calls, and diagnostic executions belong inside that selected job.
Required limits are 20 GiB RAM, 4 GiB scratch, zero swap, and no wall-time cap.
This packet neither submits a job nor changes the execution infrastructure.

## Exact snapshot inputs

Select `tests/test_hmmer_alignment_native_weight_oracle.py` as the test file.
Use the coherent application snapshot already frozen by packet 526, including
both helper modules from packets 524/525 and the common normalizer. The test
imports `_normalize_easel_weights` from the shared calculation module; it does
not define another normalizer or map calculator.

`SOURCE_PINS.json` contains the finite `support_files` array. Stage all 46 listed
files preserving repository-relative layout. They comprise:

- 40 retained Easel source/header files: the seven numerical C sources and the
  complete local include closure found by static inspection, including the
  original generated `esl_config.h`.
- The retained `easel/libeasel.a` support archive.
- Retained `hmmer/src/alimask` and its companion `hmmer/src/alimask.c`.
- This packet's `weight_oracle.c`, the unchanged packet 525 `sampler_oracle.c`,
  and `SOURCE_PINS.json` itself.

The pinned native files occupy 2,453,821 bytes before the small diagnostic/test
files. The selected alimask is pinned to SHA256
`4cf273b7b4b52363468b758a39bedf8f00540b01983bf6641ffd36140afad547`.
The archive is pinned to SHA256
`94db21cb1a09e54abf99682d2120571915cdf70bfeef8b7515969691248dd48d`.
The five retained-profile source digests, every included native file digest,
both diagnostic source digests, and their byte sizes are in `SOURCE_PINS.json`.
This identifies an explicit retained HMMER 3.4 / Infernal 1.1.5 profile, with
Easel 0.49. It does not recover the original alimask compilation history.

## Environment and command

Set all three variables explicitly in the selected job:

```text
HMMER_NATIVE_ORACLE_EASEL_DIR=<snapshot>/resources/software/infernal-1.1.5/easel
HMMER_NATIVE_ORACLE_CC=<absolute path to the root-selected pinned compiler>
HMMER_NATIVE_ORACLE_ALIMASK=<snapshot>/resources/software/infernal-1.1.5/hmmer/src/alimask
```

The compiler must provide C99, `-O2`, `-fno-fast-math`, `-ffp-contract=off`,
`-MMD`, and `-MF`. Root owns pinning the actual compiler, compiler/linker
subprograms, system C headers/runtime, libm, and pthread support. Native include
paths and the Easel archive are explicit; the test never searches the host for
Easel, a compiler, an alternative binary, or missing data. Missing/changed
inputs are failures and are not skipped.

The exact pytest argument vector, after the root-selected Python executable, is:

```text
-m pytest -q -p no:cacheprovider tests/test_hmmer_alignment_native_weight_oracle.py --basetemp <job-temporary-directory>/pytest
```

The test fixture compiles each native source in `compile_native_sources` to a
separate object inside pytest's retained temporary directory. The compile
argument vector is:

```text
<CC> -std=c99 -O2 -fno-fast-math -ffp-contract=off -I <staged-Easel> -MMD -MF <object-depfile> -c <source> -o <object>
```

`weight_oracle.c` includes the original `esl_msaweight.c` without editing it.
Its linked numerical objects are `esl_tree`, `esl_distance`, `esl_msacluster`,
`esl_cluster`, `esl_vectorops`, and `esl_rand64`. The unchanged sampler harness
links the same compiled `esl_rand64` object. Each link argument vector is:

```text
<CC> <harness-object> <listed-numerical-objects> <staged-Easel>/libeasel.a -lm -lpthread -o <diagnostic-binary>
```

There is no `make`, configure run, native-source rewrite, alternate numerical
implementation, or invocation of alimask in this fixture. The compiler's
`--version` call also occurs only inside the root-owned job. Compiler temporary
files and all constructed inputs/outputs are placed inside pytest's job-local
temporary directory. No process timeout is introduced.

## Outputs to retain and inspect

Retain the entire `--basetemp` tree and the enclosing lifecycle receipt. The
fixture writes under `hmmer_native_weight_oracle*`:

- Verified source pins, exact selected paths, compiler digest/version output,
  per-object dependency files, full compile/link arguments and both byte streams,
  process return codes, built objects/binaries and binary digests.
- Each exact constructed alignment or vector/sample parameters, native command,
  complete actual native stdout/stderr, exit code, and Python helper/common
  normalizer result. Sample stdout retains every row ordinal, not just a digest.
- A per-case `comparison.json` only after all assertions for that case pass.

Native weights, sums, cutoffs and branches are C `%a` hexadecimal strings;
tests compare exact decoded double representations, without tolerances.
Topology and cluster identifiers are compared without relabeling. DNorm
interception copies the raw vector before immediately invoking the original
native DNorm; native DScale is untouched. Singleton raw weights are the actual
native early-return values. Empty singleton GSC arrays explicitly mean no
native tree was built, rather than an invented tree. Cluster arrays are from
an independent real `esl_msacluster_SingleLinkage` call, including singleton.

The planned 57 comparisons are 15 GSC, 16 BLOSUM, 6 shared-normalizer, 17 native
Deal index arrays, and 3 native MT word streams. The N=50,001/m=10,000/seed=42
and N=130,001/m=10,000/seed=42 cases exercise initial A and D-to-A respectively;
N=130,000 checks the strict switch boundary. Positive seed 1/UINT64_MAX,
nondefault seed 43, m=1, m=N, and safe integer boundaries remain direct helper
API tests. They do not reinterpret the retained alimask CLI seed: its effective
PB configuration is still 42. Native m=0, seed=0 and signed-overflow setups are
excluded rather than executed to obtain undefined or nonreproducible output.

The cases are constructed diagnostic inputs. Their actual C outputs become
conformance evidence only when root runs the job. Full-map/native CLI,
sampling eligibility/fallback, child-owned Workflow returns, saved-only
recalculation, and closed replay belong to packet 526/root. No result in this
packet alone completes those paths or an inventory row.
