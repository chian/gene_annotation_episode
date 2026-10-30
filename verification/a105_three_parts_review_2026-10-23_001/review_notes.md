# A105 scoring sheet and readers — unadopted review example

**The scoring rubric here is the scoring sheet/format/template.** Separate
deterministic Python reader functions populate it. It contains no point scale,
grading policy, annotation-credit formula, continuation rule, or extra model call.
The investigation prompt insert is a separate review artifact owned by the parent
task. None of these files changes production behavior or a saved run.

Every protein, substrate, product, measurement and source below is **synthetic**.
This makes no scientific claim about ybhP or any real homolog.

| Sheet field | Meaning and source |
| --- | --- |
| `target_question` | Existing hypothesis's target, predicate, value and context; distinct from the actual assayed subject. |
| `experiment_ref` | Explicit reference to one underlying assay. Literature and dataset views of that assay share this identity. Equal numbers or a shared paper do not establish identity. |
| `assayed_subject_refs` | Protein/construct actually assayed; does not become a measurement on the target. A characterized close homolog belongs here when that is what the source assayed. |
| `source_claim` | Already recorded source claim or declared assay metadata, using existing `SOURCE_CLAIM` meanings; includes what substrate became what product, what was transported, or what bound. The reader copies it; concentration growth alone does not establish catalysis. |
| `conditions`, `controls` | Recorded context attributes, units and sample identities. In this example, 30 C, pH 7.5 and a protein-free blank. |
| `native_measurement_series` | Actual calibrated concentration/time values; existing number atoms retain unit references, bounds, approximations and reported uncertainty. Missing uncertainty does not mean exact measurement. |
| `derived_measurements` | Explicit arithmetic operation and selected operands/window. Here, an ordinary least-squares net product-formation rate; no kcat or statistical significance is inferred. |
| `target_correspondence` | Exact subject-identity comparison plus existing assessments when supplied. Relation/applicability/qualifications are copied from those records, never assigned by this reader. With none supplied, interpretation is unknown. |
| `provenance_views` | Both input routes' source/observation references and exact UTF-8 source-row anchors; links map each view back to the same measurement-series cells. These are two views of one experiment. |

The paired product-assay example is deliberately small. A full A105 sheet can
retain binding/transport native quantities under the same source-claim and
subject/context meanings; this example's CSV adapter and rate calculation only
handle the declared paired calibrated product-concentration assay. They do not
claim a universal assay reader or kinetic fitter.

| Time (min) | Protein sample product (µM) | Protein-free blank product (µM) | Net product (µM) |
| --- | --- | --- | --- |
| 0 | 0 | 0 | 0 |
| 1 | 2 | 0.2 | 1.8 |
| 2 | 4 | 0.4 | 3.6 |

The actual Python return is retained in `scoring_sheet_example.json`, validated
against `sheet_schema.json`. Its concise contents are:

```text
evidence_axis: A105
underlying experiments: 1
source claim: synthetic assayed protein H; substrate S -> product P
source views: experimental_dataset, literature_finding
net product-formation rate: 1.8 µM/min over 0–2 min
rate uncertainty: unknown
target subject: synthetic protein T
assayed subject is target: false
target-correspondence interpretation: unknown
```

`populate_from_dataset` parses the retained CSV and performs the arithmetic.
`populate_from_literature` reads already recorded typed, source-anchored findings
of the same assay. Both populate identical native measurement cells and the same
derived rate. `merge_same_experiment` retains both provenance views in one assay
row. Replaying a view adds nothing; conflicting views are not averaged or silently
overwritten. This grouping is only representation; it awards no information or
annotation credit. Existing credit consumption is not wired to this proposal.

Current backend limits: Store already represents observations, contexts,
assessments and source claims, but has no universal underlying-experiment
identity. This review uses a declared common assay reference and explicit
sample/control/observation selection. No inferred equivalence, generic prose
extraction, new episode, results stage or LLM grader is claimed.

Inspected: complete domain schemas/validation and quantitative-measurement tests;
Store's observation/assessment validation, record writes/current revisions,
queries and reasoning-view/commit paths; scientific-finding validation/identity;
tool number/measurement/observation builders; the external-assay subject check.
`AGENTS.md`, `GOAL.md` and `docs/TASK_AND_STEERING.md` were read. The unadopted
rule-interpreter scoring files/publication were not used as authority.

Verification command:

```sh
python3 -m unittest discover -s verification/a105_three_parts_review_2026-10-23_001 -p 'test_populate_sheet.py' -v
```

This checks both actual reader returns, schema compatibility, retained source
anchors, the 1.8 calculation, one-experiment merging, replay/conflict behavior,
and preservation of a censored value with reported uncertainty. No model call,
network request, live scientific run or production test suite is involved.
