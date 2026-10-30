This verification covers the HMMER API publication and existing typed-result
return path. It owns only the two new test files and this directory. Production
repairs were reported to and performed by the parent worker.

The executed path is the actual bound `launch` → `launch_api` → `results`
shared `method_loop`, followed by `api.hmmer.result`,
`ToolRegistry.publish_hmmer_result`, the HMMER parser/sheet/calculator facade,
source auxiliary grading custody, numerical observations, and the parent's
`execution_result_refs` admission. Decisions, continuation units, HTTP transport,
submission replies and status replies are explicit fixtures. The phmmer result
pages retain their exact historical service bytes. No new API request, HMMER
process, HPC job, database BLAST or model inference is performed.

Run and examples:

```text
.venv/bin/python verification/tool_graders_hmmer_api_binding_2026-10-24/run_verification.py verification-001
.venv/bin/python verification/tool_graders_hmmer_api_binding_2026-10-24/run_verification.py verification-002 --focused
.venv/bin/python verification/tool_graders_hmmer_api_binding_2026-10-24/save_examples.py examples-002
```

The first script records its exact pytest command, exit code, output, elapsed
time and before/after source hashes in `verification-001/` and
`verification-002/`. The example script retains
four source-backed workspaces, exact native pages, populated sheets, calculator
outputs and published observations in `examples-002/`. It recalculates each
saved sheet after Store closure/reopening, with network and native execution
prohibited. The unit test additionally prohibits ordinary file opening during
the pure calculator call after loading the saved sheet. `verification-001`
passed 57 checks in 191.40 seconds with unchanged source hashes. A later fixture
review corrected synthetic hmmscan's selected database from the phmmer fixture's
`pdb` to `pfam` and added hmmscan to the complete typed-parent-return test.
`verification-002` passed all 28 current focused checks in 191.34 seconds after
these test-only corrections, again with unchanged production source hashes.
The test groups overlap and their counts must not be added.
The two hmmscan cases in `examples-001` preserve the earlier synthetic routing
mistake and are superseded by `examples-002`; neither generation claims actual
service execution.

Checkable examples:

| Input and selected row | Native/derived measurements |
| --- | --- |
| Retained actual phmmer page 1, hit-array 0/domain-array 1 | 88 paired positions, 2 insertions, 1 deletion, 91 columns; API identity 25/89 = 0.2808988764044944; consensus identity 25/88 = 0.2840909090909091; all-column identity 25/91 = 0.27472527472527475. |
| Same retained domain | Native bias 0.03572461009025574 nats; separately derived bias 0.051539717814903775 bits; model span 89/253, sequence span 90/283, paired coverages 88/253 and 88/283; PP interval means 74.5/90 = 0.8277777777777777 and 81.85/90 = 0.9094444444444444. Actual sequence identity remains unavailable. |
| Retained actual phmmer page 2, provider index 2/original array index 0 | 73 paired positions and columns; all three displayed identity ratios are 22/73 = 0.3013698630136986; one retained hit on this page does not establish the complete three-hit population. |
| Synthetic API hmmscan | Model length 10, query-sequence length 12; 3 paired positions, 1 insertion, 1 deletion, 5 columns; API identity 3/4, consensus identity 3/3, all-column identity 3/5; domain score -2.5 bits, conditional E-value 0, bias ln(2) nats → 1 bit, PP interval means 0.6875–0.75. The reference is a profile, with no physical sequence length. |
| Synthetic empty API hmmscan | Successful complete page with zero hit/domain rows and zero scientific observations; absence of hits is not biological absence. |

The retained first phmmer target keeps native name `000058351`, null native
accession, provider target accession `6lpm_A`, and separately linked UniProt
accession `Q9RXF9`. The published reference uses `6lpm_A`; its measured sequence
length is 283, not an inferred length from the linked UniProt record.

The tests cover exact page custody, original array positions after an invalid
internal domain, duplicate provider indices, a wrong source artifact, ambiguous
score locators, missing-domain joins, valid siblings after a query-length
failure, conflicting reference lengths, missing/invalid/zero/negative values,
role inversion, PP gaps and bounds, malformed bytes, injected grading failure,
page/population completeness, empty output, wrong original query and result
identities, wrong run/scope/reference, and offline saved-sheet recalculation.

For each selected algorithm, the connected episode fixture makes nine decisions: three scientific-parent
commissions, one launch choice, three API actions and two result actions. Each
episode records exactly one local observation per selected action. The second
result child returns the same four phmmer or one hmmscan numerical observations with zero new
operational gain. Replaying the original result action changes neither its
saved return nor the completed local observations. Grading adds no model call,
action or controller observation. Full grading sheets and raw domain alignments
are absent from the captured automatic decision contexts.

Two initial production defects were reproduced and reported: a non-object
domain caused whole-page projection loss, and a missing reference length
discarded otherwise valid domain measurements. The parent added per-row type
handling and component-specific coordinate/length handling. The regressions
retain later valid domains and the missing-length domain's -2.5-bit score and
paired-position count without inventing coverage.

The following boundaries remain explicit:

- The catalog test proves that the real operation name, description, API resource
  metadata and substantive result manual are available and agree. It does not
  prove the still-missing resource-specific `child_tool_info` construction and
  automatic substantive instruction handoff. No completed manual-read action
  was inserted to simulate that missing path.
- `ModelConnection._presentation` currently renders published scientific
  contexts as TASK/STEERING, but generic API/results contexts still use its JSON
  fallback. These tests establish absence of new full HMMER grading payloads;
  they do not establish removal of tracking identifiers/hashes or complete
  TASK/STEERING rendering for resource children.
- Positive and empty API hmmscan examples are synthetic. No live hmmscan API
  execution is claimed. The B003 path
  `validation/fixtures/provider_identity_feedback/hmmer_result.json` was absent
  in this checkout, so it was not used as claimed native evidence.
- This is engineering verification with explicitly scripted choices, not a
  configured-model annotation investigation, scientific completion claim,
  W05 credit-aggregation change or native/HPC HMMER binding verification.

The immutable active goal's objective and entire DESIGN PRINCIPLES block were
reread verbatim after substantial source/native review and at completion,
followed by B003. No shared production file, inventory row or another worker's
test was edited by this worker.
