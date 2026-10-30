# Aurora workspace directory

Observed 2026-10-22 UTC for user chian. This is a directory of actual locations;
long-term retention and organization are being discussed with the user.

## Project storage and allocations

| Purpose | Location or allocation |
| --- | --- |
| Existing personal BioReason workspace | /lus/flare/projects/BioReason-Aurora-Test/chian |
| Existing repositories in that workspace | /lus/flare/projects/BioReason-Aurora-Test/chian/repos |
| Existing job artifacts | /lus/flare/projects/BioReason-Aurora-Test/chian/runs |
| Existing personal caches | /lus/flare/projects/BioReason-Aurora-Test/chian/.cache and model-cache |
| Existing shared Gentner deployment | /lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline |
| Gentner source, chrisagrams/gentner-ave | /lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/repos/gentner-ave |
| Gentner Python environment | /lus/flare/projects/BioReason-Aurora-Test/gentner-pipeline/venvs/gentner |
| Existing data-lake directory, contents not inspected | /lus/flare/projects/BioReason-Aurora-Test/cgrams/gentner-data-lake |
| Other funded Aurora project | /lus/flare/projects/EpiCalib; existing personal subdirectory chian |

/flare/BioReason-Aurora-Test resolves to /lus/flare/projects/BioReason-Aurora-Test.
Use the explicit canonical path above in saved job commands.

BioReason-Aurora-Test allocation 16458 / suballocation 16446: expires 2026-11-15;
observed available balance 39,961.8 node hours. EpiCalib allocation 14290 /
suballocation 14198: expires 2026-11-01; observed balance 130,671.5 node hours.
Balances and dates are observations, not promises of future availability.
Refresh using sbank-list-projects -u chian -r aurora and
sbank-list-allocations -u chian -r aurora.

## Current gene-annotation compute test

Run directory: /lus/flare/projects/BioReason-Aurora-Test/chian/runs/gene-annotation-aurora-20261022T151552Z
Requested work: compare the gene_001/ybhP protein with 17 existing reference
proteins using Gentner AnalysisExecutor and Biopython global BLOSUM62 alignment.
Source/environment above are reused without changing them. Inputs, driver,
outputs, temporary files and caches stay in this run directory. PBS identity
and actual outcome belong in its receipts; staging does not establish execution.

## Storage and execution facts

Keep this small index in home. Put environments, datasets, caches and job output
in the relevant project workspace. Home quota observed: 150 GiB soft limit,
165 GiB hard limit, about 41.5 GiB used. Lustre reported default group quota
settings for BioReason; an explicit numeric project quota was not established.
Filesystem-wide free space is not a personal quota.

The shared gentner-pipeline has its own AGENTS.md, MEMORY.md and active RAB
stage instructions. Read them before changing that project. This independent
protein test does not advance or validate its RAB stages.

Aurora debug queue observed: 1-2 nodes, minimum walltime 00:05:00, maximum
01:00:00. Submit from project storage. Launch compute work with mpiexec inside
a PBS allocation. No large data or software installation is needed for this test.

## Still to organize with the user

- Renewal or relocation after the allocation expiry, and durable backup location.
- Final gene-annotation workspace layout beyond this individual test run.
- Polaris and the separate tailnet Spark host have not been exercised here.

## 2026-10-22 execution result and storage clarification

PBS job 8953621 completed the independent gene-annotation alignment test on
x4418c4s1b0n0. Driver exit code 0; all 17 reference comparisons returned through
the existing Gentner executor. Driver elapsed time: 58.91138992505148 seconds.
The run directory above contains native alignment scores, executor result/trace,
input and source hashes, allocation facts and completed PBS statistics.

Compute allocation expiry does not itself establish storage project end.
ALCF documents that Gecko home and Flare project storage are not backed up.
Project-end retention rules and any separate storage allocation must be checked
before deciding a migration date. Keep an independent copy of this index and
irreplaceable results.
Sources:
https://docs.alcf.anl.gov/account-project-management/allocation-management/allocation-management/#allocation-expiration
https://docs.alcf.anl.gov/data-management/filesystem-and-storage/#disk-storage
https://docs.alcf.anl.gov/policies/data-and-software-policies/data-policy/#disk-capacity-and-retention-policies
