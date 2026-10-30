# Root verification of alphabet and AFA/A2M input decoding

The original user-entered goal remains authoritative. This records verification
of input readers, not a new goal or completion of the HMMER episode path.

The existing frozen 529 lifecycle ran these selected checks with 20 GiB memory,
4 GiB scratch, zero swap and no imposed wall-time limit:

| Attempt | Executed result |
| --- | --- |
| check007_input_alphabet | 27 tests and 117 unittest subtests passed, 0.20 s |
| check008_input_fasta | 86 tests passed, 0.26 s |
| check009_input_native | 201 tests passed, 4.17 s |

The 201 native comparisons comprise 36 classifier cases, 116 format-specific
alphabet scans and 49 AFA/A2M open/read cases. The diagnostic was compiled from
the 12 selected original Easel C units plus the retained support archive. Native
sources were not edited. The wrapper records the actual classifier counts,
selected alphabet and read output; it does not supply expected scientific
results or replace production calculations. SOURCE_PINS.json and the retained
compile/invocation records identify the exact inputs.

The original check009 handle was observed terminal and quiescent, then collected
with return code 0. Unit: gene-local-job-1f7aacb6c8644cbca925138cee5ed4b1.service.
Source, dependency, standard-library and executable pins were unchanged. The
execution audit has no outside imports or unbound mappings, and confirms native
libraries and retained fixtures unchanged. Root independently compared all three
selected production modules, their three test files and input_observer.c with
the frozen tested snapshot; every comparison matched.

Concrete retained-output example: a2m_insertions/emitted.out decoded to five
rows and 17 columns, with RF xx.xxx.xxx..xxx.x. The original native diagnostic
returned the same dimensions, digital rows and RF. This fixture covers internal
insertions; leading/trailing insertions are separate authored cases. This is
alignment-format evidence, not a new gene annotation.

Receipts, audit, invocation outputs and pin comparisons are retained under
verification/tool_graders_hmmer_map_verification_2026-10-28_529/check007_input_alphabet,
check008_input_fasta and check009_input_native. Root reviewed the complete
observer and native comparison tests and the corresponding reader contracts,
then reread the original goal objective and all ten operating principles.

Remaining: native comparison of the other newly authored formats, connection to
the existing preparation sheet/calculators, saved-data validation and requested
episode-return verification. No new API/HPC run, message-template acceptance or
complete HMMER resource capability is claimed.
