# A105 experimental database integration

The agreed scope adds experimental database search and reading to the existing
A105 literature workflow. Provider records are another representation of
experimental sources. Scientific assessment remains organized by protocol and
quantity, with the existing reliability, validity, relevance, attribution and
A105 aggregation schema.

The implementation supplies explicit search/read operations for SABIO-RK,
BRENDA, PubChem BioAssay, ChEMBL and MaveDB. Each acquisition retains original
bytes, its selected request, transport outcome and pagination. The shared
record reader exposes native measurements and source selectors. The existing
assay grader accepts authenticated database measurement selectors for effects;
other operands require the applicable existing source readers. The public
BRENDA HTML route uses the ordinary literal-source readers.

## Source handling and scoring

Search results are discovery leads. The model selects records, reads the actual
assay and its publication, and assesses construct correspondence before choosing
an assay protocol. Source snapshots retain the selected request, original bytes,
transport status and continuation. A failed or truncated request is unavailable,
and an empty page describes that query only.

The database measurement reader authenticates native cells against those
snapshots. SABIO-RK parameters and ChEMBL activities retain their original
measurement type and qualifiers. PubChem result cells require the matching assay
description; MaveDB scores require matching score-set metadata and a declared
score column. A relative binding score retains its native scale. BRENDA HTML
with a charset parameter receives the same readable projection as plain HTML.

BRENDA's enzyme pages also use div-based tables and can exceed several
megabytes. The reader retains their section labels, column headers, row IDs,
locations and citation links, including expanded detail rows. Literal compound
filters can narrow these records by organism, section and other source text.
Collapsed summaries and expanded rows remain representations to interpret;
they are not automatically separate experiments. Record and whole-page link
pagination have separate continuations.
The public full-text search can first return category counts. Its literal
category links are exposed as `search_result_queries`, and `result_field`
retrieves the selected category's hits through the same search tool. Synonym
and recommended-name search fields retain their distinct provider categories.
The additional `public.brenda.graph_search` operation searches the provider's
public prototype graph using bounded identifier or literal-text queries. It
retains the original typed bindings, publication identifiers and explicit page
continuation. Those records lead to enzyme-page and publication reads; graph
coverage does not establish experiment absence or supply kinetic measurements.
This route follows BRENDA's [public graph documentation](https://sparql.dsmz.de/brenda)
and [service announcement](https://www.brenda-enzymes.org/news.php?news_id=2025-09-01-sparql).

One live BRENDA page declared UTF-8 but contained eight invalid bytes. The
projection now preserves valid UTF-8 and renders undecodable bytes as explicit
hex escapes, with original byte offsets in decoding metadata. Original bytes
remain unchanged. This does not assign an encoding or scientific meaning to the
invalid characters. Projection failures retain the original source and an
explicit diagnostic artifact instead of being misclassified as invalid input.

Saved effects feed `literature.assay_grading.populate`, with source-anchored
experiment and assertion records. Existing readers supply any supported
variance, controls and model operands. The existing A105 aggregation combines
selected experiment sheets. Provider labels do not become numerical confidence,
and missing inputs remain unavailable. The model must connect repeated paper
and database representations to the same experiment; stable native measurement
keys additionally preserve ownership across repeated database retrievals.

Recovering a measured effect does not necessarily yield an overall scalar
subscore. The current overall evidence calculation requires suitable uncertainty
and independent assertion/alternative predictions. These inputs must come from
supported source/model operands; the integration supplies no defaults for them.

## Workflow repairs exposed by live runs

Early full runs exposed interface failures before scientific assessment:
operation arguments were generated before their operation discriminator, named
term references were generated before their value type, and reasoning records
could be presented before the terms they referenced. Generation now presents
discriminators first and reasoning sections in their actual commit order.
Accepted scientific values and scoring formulas are unchanged.

The grader contract now advertises its required experiment reference and the
criterion keys belonging to the selected assay type. Prompts show received
record and artifact identifiers as usable operands, including identifiers for
newly committed references. The parent prompt distinguishes its commissioning
operations from the child operations it can request. These changes let the
model use the same source, reasoning and scoring contracts autonomously.

A later BRENDA run selected a valid table value but used the scalar shortcut,
which requires an adjacent unit, then saved an empty effect after rejection.
The existing kinetic reader already supports a single parameter with a separate
header unit. Its operation description and the grader's operand guidance now
explain that route explicitly, including the returned component used by the
grader. This changes reader selection guidance, not the reader's acceptance
rules, numerical values or scoring formulas.

Several longer runs also stalled while emitting whitespace after an incomplete
JSON response. The provider now interrupts 4,096 consecutive whitespace
characters outside JSON strings and allows one request for a complete response
in the same conversation. It retains the original stream, interruption and retry
input. It does not repair malformed JSON or execute the interrupted proposal.
Only a completed response enters the existing parsing and action validation.
Interruption and terminal-status handling follow the documented
[Codex app-server lifecycle](https://learn.chatgpt.com/docs/app-server#lifecycle-overview).

## Full workflow examples

The evaluator keeps these expectations outside model input. The workflow gets
only an anonymous raw sequence and the general A105 task.

| Molecule | Expected source opportunities | Assessment question |
| --- | --- | --- |
| E. coli FolA/DHFR | SABIO-RK entry 100; ChEMBL target CHEMBL1809 and assay CHEMBL666737 | Recover measured enzyme kinetics and inhibition, with construct, substrate, conditions and units. SABIO entry 100 reports kcat 6.18/s and Km 0.89 µM at pH 7 and 15°C. |
| E. coli LacZ | BRENDA EC 3.2.1.23, reference 701079 | Recover preparation/tag-dependent activity comparisons and their original experimental support. |
| E. coli AmpC | PubChem AIDs 584, 585 and 1003 | Recover hydrolysis/inhibition measurements, paired detergent conditions and confirmation. |
| Streptococcal protein G | MaveDB urn:mavedb:00000105-a-1; PMID 25455030 | Establish the GB1 domain construct and interpret relative IgG-Fc binding, background controls and variant normalization. |
| E. coli YkfM | Hypothetical-protein control from the earlier A105 runs | Preserve unknown molecular activity and distinguish phenotype evidence from a direct molecular assay. |

Reusable live driver: `tests/live_a105_database_workflow.py`. Generated states,
snapshots, transcripts and reports belong beneath `runs/`. No targeted tests are
part of this work. Successful retrieval alone does not establish a completed
scoring run. Final reports must distinguish source discovery, native measurement
recovery, saved assay grading and actual aggregation, including unresolved scores.

The optional `--database-focus` argument centers an entire autonomous A105
investigation on one provider and its cited publications. It supplies no
molecule identifier, expected record, measurement or scripted action. It was
used for the full BRENDA follow-up after the initial general workflows exposed
its page-format failure. Evaluator expectations remain outside the model input.

## Observed live outcomes, 2026-11-02

Anonymous sequence-only workflows exercised database discovery, native readers,
assay grading and A105 aggregation. These are observed outcomes, not hard-coded
expected values or targeted tests. The evaluation accepted other relevant
experiments when the model discovered them instead of the evaluator's example ID.

| Source | Observed result carried into an assay sheet |
| --- | --- |
| SABIO-RK | E. coli DHFR entry 100: kcat 6.18/s, stored as 370.8/min. Additional LacZ and AmpC kinetic measurements were recovered. |
| BRENDA | LacZ reference 706614: native turnover 620/s, stored as 37,200/min. The ordinary kinetic reader preserved the separate header unit and supplied the existing assay grader. |
| PubChem BioAssay | AmpC assay 1801578: reported inhibitor IC50 25.4954 µM, with the matching assay description and result definitions. |
| ChEMBL | AmpC assay CHEMBL649554: reported activity 1.3 µM. The run retained the provider's homologous-target assignment as an attribution limitation. |
| MaveDB | Protein G score set urn:mavedb:00000105-a-1: native score 0.41564494188558937 for p.[Thr10His;Val38Ile], qualified to the experimental GB1 construct and variant. It is not a whole-protein wild-type affinity. |

The YkfM control produced no direct molecular-assay sheet. Its phenotype evidence
remained scope-limited and did not discriminate the proposed porin function.
This is an unresolved function, not proof that no experiment exists.

BRENDA category searches repeatedly returned retained HTTP 504 failures. In a
fresh full workflow, the model independently selected the public graph search,
recovered 15 linked records from its sequence-derived accession, and opened a
cited BRENDA experimental record. The returned graph labels contain enzyme
names; the final record projection obtains page-read identifiers from their
native EC/reference URIs. That small projection correction followed inspection
of the live response; the frozen run itself retains the earlier projection.

The saved runs contain 30 assay sheets and 22 aggregation invocations. These
counts include repeated assessments and are not counts of independent
experiments. The native-measurement ownership review found no measurement key
assigned to multiple experiment references. Cross-publication/database identity
still depends on the supported source interpretation.

**Full numerical scoring was not demonstrated.** The aggregate reliability,
validity, relevance, attribution and overall values remained unavailable.
Saved cells identify missing or unselected variance, controls, sampling meaning,
assertion/alternative predictions and model inputs; some scientific criteria
also remain unresolved. Recovery of an effect does not establish those operands,
and the existing scoring policy was not changed to manufacture a number.

One DHFR child produced an accepted partial report. The remaining investigations,
including a substantive DHFR follow-up, were stopped by the operator after the
integration evidence was captured; no outer workflow completed. Their controller
continues while the estimated marginal finding-credit upper bound exceeds its
default cost of 0.001. A saved aggregate is not a termination condition. These
stops are preserved explicitly and must not be described as successful full
workflow completion.

The final action/context-lookup review found no attempted BLAST or other homology
search. Four keyword matches were source inspection and qualification of
ChEMBL's target-assignment label, not search invocations. The A105 prompt uses
positive experimental scope and the available operation catalog.

Final evidence and exact model input are preserved beneath
`runs/a105_database_integration_2026-11-02_014/`:

- `completion-evidence.json` and `.md`: saved effects, grades, aggregates, returns,
  failures, ownership and scope-review candidates from runs 008, 013 and 014.
- `brenda-search-evidence.json`: classic-search failure, successful graph search
  and subsequent experimental-record read.
- `continuation-diagnosis.json` and `.md`: actual continuation operands and why
  the other investigations had not returned.
- `a105-role-prompt.txt`: exact A105 task text from the frozen source.
- `case_b/a105-initial-prompt.txt`: actual assembled initial child prompt,
  accompanied by request provenance and hashes.

Run 013 additionally retains `brenda-grader-handoff.json`, which connects the
620/s source measurement to its saved grade and aggregation. No targeted checks,
unit tests or pytest executions were used for this integration.
