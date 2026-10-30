The existing full `tests/test_bvbrc_alignment_episode_flow.py` suite passed: **12 passed, 0 failed, 0 errors, 0 skipped in 5871.78 seconds**. One pytest process ran, without a restart. Its actual exit status was 0. The three fixtures exercised the unchanged Workflow → scientific child → launch → API → results → scientific parent → root path using scripted choices, controlled loopback HTTP replies and retained native bytes.

The child command was:

```sh
.venv/bin/python -m pytest tests/test_bvbrc_alignment_episode_flow.py -vv --junitxml=verification/tool_graders_bvbrc_alignment_workflow_2026-10-25_162/pytest.junit.xml
```

`command.json` records the exact absolute argv and working directory. Pytest PID 1057060, wrapper PID 1057037 and exec session 86263 identify the actual run. It started at `2026-10-25T12:27:08.797883+00:00` and exited at `2026-10-25T14:05:00.883007+00:00`; wrapper elapsed time was 5872.085130516905 seconds. The complete stdout/stderr is `pytest.log`, and `pytest.junit.xml` records every test outcome and duration. `process-terminal.json` contains their hashes. `assessment.json` summarizes the terminal result.

These actual numbers reached both original typed parent boundaries:

| Case | Verified numerical return | Retained native artifacts |
| --- | --- | --- |
| MSA ordinary DNA alignment | 4 members; 28 cells; 6/28 gap fraction; column 1, zero based, entropy 0.9182958340544896 bits; native score 92 | Aligned FASTA, frequency table and consensus FASTA |
| MetaCATS files | 12 members; chi-square 8.330556481172943; calculated p 0.0038983714243371837; native exported p 0.00389837142433717; biological A/C counts [6, 0, 0, 6] | Original FASTA, metadata TSV and filtered chi-square TSV |
| MSA Mauve blocks | Block 0, members 1/3: 39 identical canonical sites, 7 substitutions, 46 comparable sites and identity 39/46 = 0.8478260869565217 | Complete six-block XMFA |

`independent-retained-numbers.json` supplies a separate arithmetic check using only the Python standard library and the unchanged retained bytes. The MSA entropy population is [A, A, internal dash], excluding the other member's terminal dash. MetaCATS uses raw [[6, 0], [0, 6]], epsilon 0.001 per cell, expected counts 3.001, continuity delta 0.5 and df 1; independent chi-square is 8.330556481172945 and the df-1 erfc tail is 0.003898371424337174. Those small floating-point differences agree with the production values within the recorded 1e-14 relative tolerance. XMFA counts independently match 39/7/46. This arithmetic check ran no Workflow, acquisition, production parser or native scientific program.

Each case passed all four checks: selected three-slot construction and child-owned HTTP; full artifacts/sheets/components and both typed numerical returns; controller and observation accounting; and saved calculation/replay. The MSA and MetaCATS cases retained and reread earlier partial publications, selected their next missing-artifact acquisition, and returned the later numerical result despite reversed operation-hash sorting. MSA did not complete while the explicitly required consensus bytes were missing, even after the requested numbers were available. Forged values and an added unrequested numerical field were rejected.

Saved-sheet recalculation reproduced the original components and changed results when explicit parameters changed, with acquisition and native parsing blocked. Subsequent saved execution replay, result reads, return validation and admission ran with the existing scientific-calculation barriers, including the lower-level XMFA and statistical barriers. All recorded action, scripted-call, observation, report-attempt and receipt counts stayed unchanged; each replay made zero new HTTP calls. The actual strict-barrier receipts list 140 scientific symbol names plus the suite's earlier acquisition/native-parser blocks. Historical diagnostic counts are not substituted for this run.

| Case | Completed actions / observations | Scripted calls | Used paths at final source guard |
| --- | --- | --- | --- |
| MSA | 25 / 25 | 26 | 293 |
| MetaCATS | 25 / 25 | 26 | 294 |
| XMFA | 21 / 21 | 22 | 291 |

The extra scripted call in each case is internal report redelivery, with no extra completed action or observation. Root and scientific episodes each retained eight zero-gain observations and used the ordinary estimator: final expected-gain upper bound 0.07619158557694622 was below caller cost 0.1. Launch, API and results retained final actual gains 2, 2 and 3 respectively, then exact-zero future bands through the existing practical endpoint. Their action counts were 1/2/6 for MSA and MetaCATS and 1/2/2 for XMFA. No controller, estimator, turn cap or completion rule was changed.

All Workflow-closure and after-tests source guards passed, with no changed/deleted used file and no used file lacking its original BEFORE hash. All configured facade and scientific binding pin checks passed. The unchanged test SHA256 is `097957e2e5efaf2892fac05c1c6528af760ea6aaa4f0f78a1c0e33d9246a447d`. The shared adapter pin is `b528f6c617d9e08a3068e2abce17f583aa014dfa3eeb72c9dfb643aef54e08ca`; the scientific binding pin is `3d24bf5740f2b28bc8aa17d34c9ee0ccb680f58875eb409c837dd990cfe45059`. These are fresh prospective pins, not changes to earlier receipts.

The broad before/after manifests contain no changes to pre-existing source files. They separately record seven new unimported proteome files added by other work: the native module/contracts/schema/test and the data contracts/schema/inputs. They were outside the actual used-source closure. No guard was relaxed. `case-msa_dna.json`, `case-metacats_files.json` and `case-xmfa_blocks.json` preserve the actual guards, pins, numerical values, HTTP calls, archived estimates and receipt hashes.

The new fixture directories are `runs/msa_dna-no78l7n3`, `runs/metacats_files-osqnpg2_` and `runs/xmfa_blocks-o7qyifem` under `verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25`. Old runs and source pins were not edited. In particular, old run009 remains its original failed fixture attempt and is not a passing baseline.

This worker changed no production or existing test source. New files under this directory comprise the single-run wrapper, read-only receipt/status collectors, independent arithmetic check, logs, hashes, progress snapshots and this assessment. Two preliminary read-only diagnostic probes used incorrect journal-column/archived-child assumptions and were corrected; neither was a pytest failure, a production defect, a source edit or a repeated run.

The required immutable goal, AGENTS.md, GOAL.md, episode/time/practical instructions, complete 819-line test and four specified prior boundary records were read. The immutable objective and complete DESIGN PRINCIPLES block were reread after source/native study and before interpreting the case outcomes. Complete additional source reads covered the alignment return owner, saved-publication reader, both adapter facades, saved projector, MSA calculator and MetaCATS biological calculator. The native examples were inspected directly.

This establishes these three controlled retained-output episode examples. It does not establish live BV-BRC access, new native MSA/MetaCATS/Mauve execution, HPC execution, configured-model annotation, deployed mode coverage or scientific credit aggregation. Scientific TASK/STEERING presentations were rendered and asserted separately from scripted `Choices.complete`; other roles' model-facing prompts and their current JSON fallback were not verified here. Original producer versions and original output-to-input mappings remain unknown/qualified: the sheets retain empty version lists, artifacts retain unverified original-path/byte-version relationships, and 1/6/9 optional requirements remain respectively. Prealigned analysis, segment alignment/concatenation, MetaCATS groups/auto, native monitoring and source-bound original XMFA coordinates remain outside this suite's complete Workflow coverage. Literature, evidence-axis work and W05 were untouched.
