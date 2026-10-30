# BV-BRC v2 shared Workflow verification

This directory records engineering integration verification of the actual
`Workflow` → `launch` → `launch_api` → parent → `results` → parent path.
The fixtures choose actions and root continuation, and replace the HTTP response
boundary. Resource completion, custody qualification, typed communication,
admission, operational credit and exact-zero endpoint estimation are production
implementations. No host qualification helper is replaced.

The count and facet bodies are the unchanged, hash-checked retained Solr native
responses from `tool_graders_bvbrc_data_contract_2026-10-24`. Expression values
come from retained native array rows reserialized into an explicitly synthetic
Solr envelope; one zero-count value is explicitly added for a missing-versus-zero
engineering test. Other page and malformed/partial cases are synthetic.

The saved structured provider decision context is verified. Actual rendered
TASK/STEERING prompts and configured-model behavior are unverified; the current
template boundary awaits the user's feedback. No live HTTP request, annotation,
literature work, W05 change or annotation-score formula change is involved.

The final focused run passed **9 tests in 167.89 seconds**. All 29 recorded
production, test and instruction-file SHA-256 values were unchanged from before
to after this run. `RUN.json` records the command, times and both hash sets;
`pytest.txt` and `junit.xml` retain its actual output. The earlier complete run
also passed nine tests, but a host edit landed while it was running, so its
separate JUnit file is preserved without a current-version claim.

Verified through actual selected episodes and saved decision contexts:

- Native count **2** with **0** document rows reaches the parent as an available
  exact count. Replaying the selected acquisition makes no second transport
  call and changes no action, observation or admission record.
- Selected expression values **-0.132**, **-0.544**, and condition duration
  **5 mins** reach the parent with their original feature/result identities.
  The explicitly synthetic count **0** remains distinct from absent count/TPM
  fields in the other row.
- Native facet counts **1, 1, 0** retain denominator **2**, fractions
  **0.5, 0.5, 0**, and the native null-term missing bucket. Its actual term values
  PATRIC and RefSeq are materialized in the parent's saved input.
- An explicitly selected second page makes exactly one additional controlled
  transport call and delivers that page's actual selected values.
- Returning the same child form again adds no completed-action observation and
  does not duplicate the parent's materialized values.
- A second local projection of the same response has the same acquisition
  identity. Its result child gains **0** new acquisition credit, compared with
  the first child's caller-selected **2** operational units, while returning
  the newly selected values.
- Reopening the saved Store and reconstructing the actual Workflow preserves
  closed observations, model-call records and admissions without a new provider
  call or transport request.
- Native partial results and a malformed requested numeric value retain valid
  raw rows and values. They give no endpoint completion proof and reach the
  results child's next saved decision through its own value channel.

Successful launch, API and results endpoints each have one completed command,
one observation, and exact-zero future expectation immediately after the actual
endpoint. The parent's final wait is an explicitly selected engineering action
used to save its subsequent decision input; it is not a resource completion
turn. Acquisition creates no annotation or scientific observation records.

`EXAMPLES.json` exports the actual episode records, selected actions,
observations, admission records and exact selected fields from saved provider
inputs for all nine cases. It includes a manifest for **34 complete retained
artifacts**, copied without reserialization into `artifacts/`. Native responses,
source-request artifacts and populated grading artifacts remain linked by their
actual identifiers and byte hashes. `collect_evidence.py` verifies byte hashes
while exporting, after requiring a passing run with unchanged source hashes.

The tests exposed two real host defects before passing: schema property-order
changes altered outer materialization order during admission replay; actual
report redelivery has no own-action row, which an admission check required.
The integration owner fixed these without changing the tests' fact/credit
expectations. This workload changed only the two new test files and this new
verification directory.

Named cross-page join inputs, supplied-unit metadata, authenticated/live service
access, every collection's deployed fields, and detached worker execution are
not covered by these nine cases. They are separate verification responsibilities;
this record does not claim the entire BV-BRC family or broader goal complete.
The original objective and entire design-principle block were reread verbatim
from the authoritative attachment after verification, followed by current
sections 10/10.1 and additive corrections 002/003 before handoff.
