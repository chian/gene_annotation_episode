# Earlier experiment-category list from this thread

This is a verbatim conversation excerpt for the requested inventory, not a new goal or instruction amendment. Only public user/assistant messages were extracted.

## user, 2026-10-27T01:07:03.569Z, transcript line 33261

Is A105 done? how many experiment-types do you have graders for?

## assistant, 2026-10-27T01:07:56.839Z, transcript line 33284

**No, A105 is not done.** There are executable graders in **6 assay families**:

1. Biochemical activity/rate assays.
2. Enzyme kinetics and substrate specificity.
3. Ligand binding and binding discrimination.
4. Transport/substrate-response comparisons.
5. NADH optical-rate assays.
6. Partner-removal/addback experiments.

There are also **2 supporting measurement families**: reported protein-signal/band ratios, and protein amount/preparation composition.

So that is **8 implemented grader families**, with some overlap—not 8 fully completed experimental graders. Each handles specific inputs; source-reading coverage, uncertainty handling and primary-paper/model validation remain uneven. General gel densitometry is still unimplemented.

## user, 2026-10-27T01:09:29.696Z, transcript line 33322

grader families are not the same as graders. For each family, there might be multiple assays. Even overlapping assays have value as extra verification since each assay has an error rate

Source: /home/chia/.codex/sessions/2026/10/25/rollout-2026-10-25T19-22-06-01a17595-fdb0-7ea1-ba23-df81f32394b0.jsonl
