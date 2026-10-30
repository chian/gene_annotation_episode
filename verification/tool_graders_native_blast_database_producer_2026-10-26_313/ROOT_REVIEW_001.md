# Root review of native database producer313

2026-10-26. This records reviewed implementation and its actual verification
limits. It does not declare any complete scientific tool or HPC deployment.

## Inspected implementation

Root read the complete producer contracts, driver and tool-information module,
then all changed regions after review corrections. Root read all three owned
test files, including the later parser-import-location regression, the example
runner, and the relevant existing PBS preparation/environment path. Earlier
310 and313 contracts remain permanent; corrections are additive002 through006.

The implementation defines closed selected-job/plan/output fields; pure
validation and command compilation; one selected subprocess and complete
artifact retention; and six explicit HPC tool-information descriptors. It does
not implement numerical grading or attach the new operation to the shared PBS,
result-worker or episode-return paths. The existing library freeze/resolve test
checks tool-info preservation, not an actual installed resource binding.

Root review identified and verified correction of these defects:

- The existing PBS preparation creates attempt-local tmp/cache directories.
  The new driver now accepts those canonical directories while rejecting
  non-directories or escaping/symlink paths. The one-attempt guard remains.
- A filtered metadata key list lost original file associations on missing or
  mismatching copies. Every selected metadata FileIdentity now has an explicit
  capture entry, including null. Deterministic descriptor-derived metadata keys
  distinguish equal-content files at different paths and allow exact shared
  descriptors to share a capture.
- Missing PSSM parser imports were classified as invalid scientific input.
  They now produce producer_input_parser_unavailable with the retained input.
  A failed test additionally exposed an editable-install fallback to this
  checkout. The driver now requires the parser in the verified selected package
  and checks its actual imported location before use.
- Episode-facing tool instructions no longer include internal workload names
  or implementation-status commentary. Substantive selected tool-use guidance
  and the separate four-field child_tool_info contract remain.

## Verification inspected

- check005:149 passing tests in36.84 seconds.
- check006:one additional parser-location regression passed in0.75 seconds;
  production contracts/driver were unchanged from check005.
- check_008:seven tool-information checks passed in1.21 seconds after the
  final instruction-text correction. These repeat the corresponding earlier
  cases; they are not seven additional distinct producer cases.
- examples002:15 complete synthetic examples,13 simulated command invocations,
  four structured failure bundles. All nine accepted program/query combinations
  are represented, along with failure and PBS-prepared-directory cases.
- Root independently checked every retained example artifact's actual length
  and SHA-256:191 artifacts,13,705,770 bytes, all matched their bundle records.
- The final successful test/example receipts each record local_jobs enforcement
  of20 GiB RAM and4 GiB scratch with no wall-time cap. No native database BLAST
  algorithm, remote service job or HPC login was run by these checks.

The failed check001 selector fixture, check004 parser-fallback regression and
check_007 runner-path invocation remain retained. Passing later checks do not
erase those earlier outcomes.

Concrete examples: native returncode7 retains partial bytes and records
native_nonzero_exit; returncode0 without the required report records
required_output_missing; two selected metadata files with the first missing
and the second changed retain [null, actual second capture] and make zero native
invocations; an unavailable PSSM parser retains the actual PSSM input and makes
zero native invocations. These examples verify reusable field-population and
validation functions. Their content is explicitly synthetic, not scientific
measurement evidence.

## Remaining work

The shared PBS/episode binding, authenticated artifact acquisition, numerical
worker, requested typed returns, scientific-record qualification and complete
episode-path tests remain unfinished for these six new modes. Actual HPC
software, prepared databases, interpreter dependencies, offline VDB settings
and native scientific output still require verification. The producer's complete
declared file inventory is not a claim of full third-party dependency closure.

The numerical grader tally remains99/308. Producer work advances execution
infrastructure for the six fixed rows and does not complete their numerical
grader/result-path requirements or remove any other fixed row.
