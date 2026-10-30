The unchanged pairwise workflow module produced **5 passed, 0 failed, 0 errors** in 837.132 seconds. Native return code: 0. This is a five-case verification on the acquired snapshot; it is not a frozen all-suite pass.

The acquisition manifest covers 1,781 copied files (34,463,979 bytes): 1,768 snapshot files and 13 authority/evidence files. Original hashes were stable across acquisition and every copied hash agreed. Source files and directories were made read-only. Before/after execution checks covered all copied files; the test's own provenance assertion stayed enabled and checked 1,257 files. All 338 loaded project and fixture modules resolved to copied files. See [snapshot receipt](SOURCE_SNAPSHOT_RECEIPT.json) and [full source manifest](SOURCE_SNAPSHOT_MANIFEST.json).

The native job used the existing .venv Python through copied production local_jobs, with 20 GiB RAM, 4 GiB scratch and no wall cap. The receipt records cgroup enforcement and measured duration. [Receipt](snapshot/verification/frozen_check_001/receipt.json), [JUnit](snapshot/verification/frozen_check_001/junit.xml), [stdout](snapshot/verification/frozen_check_001/stdout.txt), [stderr](snapshot/verification/frozen_check_001/stderr.txt).

The prior broad run remains 226 passed, 15 failed and 5 errors. All five pairwise errors arose at the final SOURCE_PROVENANCE equality assertion after nine production files changed during the long fixture. No original job, receipt, log or source file was altered. Exact prior hashes, test error text and current checks are retained in [DIAGNOSIS.json](DIAGNOSIS.json).

Actual retained numerical example from this run:

| Quantity | Value | Meaning |
| --- | ---: | --- |
| Query paired coverage | 0.6 | 9 paired nucleotide positions / 15 supplied nucleotide positions |
| Reference paired coverage | 0.6 | 3 paired amino-acid positions / 5 supplied amino-acid positions |
| Distinct aligned pairs | 3 | Three translated codon-to-residue correspondences |
| Paired identity | 1.0 | 3 identical amino-acid pairs / 3 paired columns |

The 15-nt query ATGAAAACTGGGTAA and 5-aa reference MKTGG produce the synthetic native MKT/MKT HSP. Native score 40, bit score 20 and E-value 0 are retained separately; database E-value does not define pairwise relevance. Query intervals are [0,3), [3,6), [6,9); reference intervals are [0,1), [1,2), [2,3). Database function weights and database-model parameters remain null.

The requested measurements reach the results parent and are forwarded through the scientific child's typed return. The intermediate publication retains missing values. Contradictory reference identity yields partial status and null pairwise facts. The saved-sheet/replay check forbids acquisition, preserves durable actions and forms, and adds zero native calls. See [numerical examples](NUMERICAL_EXAMPLES.json) and [action accounting](ACTION_ACCOUNTING.json).

Actual code paths exercised include input parsing, custody, selected primitive calls, manifest associations, artifact retention, Homology native parsing, pairwise sheet construction, deterministic calculations, typed returns and practical completion. Selected decisions, root/scientific continuation and NativeClient transport are fixture controls. Synthetic native bytes do not establish live BV-BRC or native BLAST execution.

No production file or original test changed. No annotation scoring, literature grading, root execution, runtime-loop behavior, resource deployment or scope accounting changed. This existing composed Workflow test does not establish independent detached execution. The remaining live-service and broad-suite claims stay unverified. [Inspected implementation paths](INSPECTION.md) and [completion review](COMPLETION_REVIEW.json) record the scope of inspection and the final authority/contract reread.
