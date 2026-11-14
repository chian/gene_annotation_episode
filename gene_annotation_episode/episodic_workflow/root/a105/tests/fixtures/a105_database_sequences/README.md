# Independent A105 discovery cases

Each `case_*.txt` is an anonymous raw protein sequence. The live A105 workflow
receives that sequence and the same general experimental-evidence task for
every case. It must discover identities, relevant sources, experiments and
measurements on its own.

`evaluator_expectations.json` belongs only to the evaluator. Do not provide its
labels, accessions, record identifiers, values, assay descriptions or expected
resource choices to the model. Do not use `--database-focus` for this evaluation.
Do not preload evidence or prescribe a search or grading action.

These cases offer the following opportunities; finding them is part of the run:

| Fixture | Evaluator identity | Resource opportunity and benefit |
| --- | --- | --- |
| case_a | E. coli DHFR | SABIO-RK links kinetic parameters to substrates, enzyme preparations, conditions and original publications. |
| case_b | E. coli LacZ | BRENDA links curated preparation/tag/variant-dependent enzyme properties to their experimental citations. |
| case_c | E. coli AmpC | PubChem BioAssay supplies matched detergent controls, confirmation assays, protocols and inactive as well as active outcomes. |
| case_d | Streptococcal protein G | MaveDB supplies variant-level binding scores, reference constructs and normalization metadata beyond article prose. |
| case_f | M. tuberculosis InhA | ChEMBL links compounds to direct biochemical inhibition assays, measured endpoint definitions, censored values and publications. |
| case_e | E. coli YkfM | Optional unresolved-function control; phenotype evidence alone does not establish a molecular mechanism. |

Alternative relevant experiments are acceptable. A provider call alone does not
demonstrate a benefit: inspect the information recovered and how it enters the
assay assessment. Keep discovery, source correspondence, recovered measurements,
saved grading, numerical subscores, aggregation and accepted episode returns
separate in the evaluation. Unused resources and unresolved requirements are
results to report, not reasons to add case-specific hints during a run.

Use `tests/live_a105_database_workflow.py` for full workflows and
`tests/report_a105_database_workflows.py` to inspect their saved state. Generated
states, source snapshots, provider responses, prompts and reports belong under
the top-level `runs/` directory. No targeted checks or unit tests are needed for
this live evaluation.
