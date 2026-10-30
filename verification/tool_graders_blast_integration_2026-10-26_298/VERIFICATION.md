# Workload 298: selected paired BLAST episode integration

This implements contract 008 for explicitly bound local pairwise blastn,
blastp, blastx, tblastn and tblastx. The implementation connects the existing
tool information and numerical fields/functions from 293/294/296/297 to the
shared Workflow and authenticated typed episode returns. Populated numerical
sheets and parent forms are verification examples, not the implementation
deliverable itself.

## Implemented path and ownership

The selected scientific process retains the evidence_axis, thought_pattern and
child_tool_info construction slots. Its ordinary launch child receives the
original job, scope, constraints and return form; launch_local executes the
selected practical.job.start. The original handoff identifies that actual native
attempt. Existing results episodes select execution.results.status or
execution.results.collect. Capture, deterministic worker grading and publication
occur inside that selected collect action. There is no prescribed status/collect
order, extra parsing episode, model grading call or private investigation loop.

Owned implementation:

- `native_blast_results.py`: original selected-action qualification, immutable
  result receipts and lookup index, retained capture, bounded grading/publication,
  requested facts, record identity, operational credit and practical completion.
- `native_blast_returns.py`: immediate-child commission, role/scope/assignment,
  successful runtime report attempt, frozen form and original numerical facts;
  later scientific forwarding contains only actually admitted facts.
- Narrow additions in `execution_episodes.py`: explicit local binding/schema,
  substantive tool contracts and commission route, selection/catalog/dispatch,
  discovery, facts, receipt admission, reference resolution, credit and completion.
- Narrow additions in `execution_progress.py`: actual native program/pairwise
  mode, original selected outputs, status meanings and selector/grader functions.
  Generic local monitoring instructions retain their existing ownership.
- The root-authorized change in `infernal_result_presentation.py` extends its
  existing mechanical receiver filter to the exact paired-BLAST host marker.
  Full stored observations remain authoritative; automatically hydrated records
  cannot add unrequested BLAST measurements to parent decision presentation.

Other workers own acquisition/lifecycle, worker/publication/views, native
parser/calculator mathematics and host marker validation. Root owns the actual
`knowledge/index.json` entry, progress accounting and alignment-site work.

## Authentication and frozen history

Each receipt is tied to the original saved BindingContext, selected own action,
results assignment, scope, handoff/target, intent, observation, assignment manifest,
capture intent/plan, immutable receipt and original completed action outcome.
Original bundle/run/episode/attempt/operation/request/resource and allocation
must agree. Full captured files, source content and source identity must agree.

The publication validator from 297 compares exact selected rows and complete
stored HSP observation payloads against retained frozen row artifacts, including
query/reference identity, native row, host marker, measurements and intervals.
Union rows retain null observation references. They summarize the original HSP
correspondence without creating another observation or acquired-record credit.

The two numerical x-sources are `execution_blast_pairwise_hsp_rows` and
`execution_blast_pairwise_union_rows`. Numerical sources are populated only when
requested. Scientific forwarding uses `execution_blast_pairwise_result_refs`;
the generic execution_result_refs is this provider's source only in its own
results episode. Row, original artifact-key and search-pointer namespaces resolve
only against exact own/admitted rows. Possessing a source does not authorize an
unrequested row, sibling return or whole sheet.

Completed replay and redelivery read original retained facts. They do not read
the live attempt, submit work, parse reports, recalculate numbers, publish Store
records or add runtime actions/observations. Caller-owned operational units and
stable record identities are reused. A successful terminal attempt with complete
capture and valid requested numerical output gives the existing practical
completion proof only after the selected own action is saved as completed.
The existing estimator then sets future expected gain to exact zero while
preserving the actual final gain.

## Concrete full-path verification example

The real native verification job is reverse translated BLASTX on supplied
sequences and an explicitly selected interval. It follows annotation parent →
scientific_process → launch → launch_local → original handoff → results →
scientific typed return → annotation parent, using actual Workflow/method_loop.
Choices and the scientific fixture horizon are scripted engineering controls;
native execution, lifecycle, bounded grading, Store, typed forms and practical
completion estimation are production implementations.

The requested HSP form returns paired_positions=62 and
query_aligned_positions=186. The requested union form returns query_length=244,
query_paired_coverage=186/244, query_selected_length=186,
query_selected_paired_positions=186 and query_selected_paired_coverage=1.
Original JSON coordinates stay query_from=30, query_to=215, query_frame=-3.
The published query interval is [29,215) nt with amino-acid model units.

Three result selections share one source and one genuine HSP observation.
The third selects only native_score_bits=132.494 for the same stable HSP. The union
creates no observation. The intermediate scientific child forwards exactly
two requested HSP rows (different metric selections) and one union row.
No unrequested native_evalue or native_raw_score appears in its parent-facing
STEERING presentation, while the stored HSP contains all numerical components.

The complete example has exactly 13 selected actions, 13 local observations
and 13 scripted decision calls: annotation parent 1, scientific process 4,
launch 1, launch_local 1 and three results episodes with 2 each (explicit status
then collect). The first result episode gains [0,6] using the supplied acquired
record unit 2 for source/reference/HSP; later selectors gain [0,0]. Launch_local
gains 7 and launch gains 3, both caller-defined operational units. Each practical
endpoint has exact-zero future expected gain after its final actual action;
there is no additional zero-gain turn. Child inputs contain no ancestor yield
history.

Successful no-hit capture returns an empty HSP set with completed=true and no
HSP observation. Changed stdout or missing report preserves surviving files and
explicit failures, with completed=false. A native nonzero return remains an
actual failed native attempt; it is not converted into scientific completion.
Source-only and completion-only requested forms do not import numerical rows.

## Verification records

All runs use `.venv/bin/python` through `local_jobs`, 20 GiB RAM, 4 GiB scratch,
zero swap and no wall cap. Native children and deterministic grading workers use
the same explicit policy. The lifecycle records the actual scratch monitor
semantics (visible allocated bytes with possible overshoot), and enforces a
per-file hard limit; it is not a filesystem sandbox. Complete stdout/stderr,
native outputs, Store state, action/capture/grading receipts and forms remain
under the retained test directories.

| Run | Result | Meaning |
| --- | --- | --- |
| first_checks | 1 failed, 3.07 s | Closed communication schema rejected unconstrained search-key strings. 297 corrected identifier namespaces and explicit enum string types; communication validation was preserved. |
| schemas_first | 5 passed, 19 deselected, 8.16 s | All five actual bound program/software schemas. |
| second_checks | 51 passed, 1 failed, 292.59 s | Full native path and return admission passed to the failure; changed-stdout fixture used stdout.log rather than the declared stdout.txt. |
| third_checks | 2 passed, 1 failed, 14 deselected, 67.17 s | Corrected stdout fixture exposed another fixture assumption: the selected reverse blastn report was genuinely zero-hit. The positive partial-capture example now selects 294's retained positive forward interval without changing native data. |
| fourth_checks | 14 passed, 14 deselected, 141.68 s | Partial/zero/native failures, original observation/form/action tamper and frozen replay. |
| complete_checks | 44 passed, 1 failed, 168.07 s | Return admission and real translated Workflow passed; the new unsupported-resource fixture used the unknown configuration label hpc instead of the actual pbs_ssh binding. Generic configuration validation rejected it correctly; the fixture is corrected. |
| final_checks | **97 passed, 287.30 s** | Both owned test files (69 tests), existing execution-family/progress tests, HMMER original-result replay and two Infernal receiver-presentation cases (28 regressions). |

`final_checks/receipt.json` reports returncode 0, changed_sources=[], actual
20 GiB memory, zero swap, runtime_max=infinity and 52,748,288 observed scratch
bytes. The entire top-level production package, shared method_loop sources,
selected test files and exact addenda have before/after
SHA-256 snapshots. `FINAL_SOURCE_HASHES.json` is the final run's after snapshot,
not a claim about later unrelated edits. Root was notified after this snapshot
completed so its separate native-HSP site reader work could proceed.

The run launcher's knowledge snapshot mistakenly targeted ROOT/knowledge instead
of the actual gene_annotation_episode/knowledge. The original manifests remain
unchanged. `LIBRARY_SOURCE_SHA256.txt` supplies a clearly separate post-run
snapshot of the real index and instruction files plus root's retained
knowledge_check001 receipt/result/frozen index. The actual index SHA-256 is
424f7a35ea822ba3e0c227a1e21cd54d5f5bd769681b25acb3b381be08ce3ce1.
Root's frozen retrieval example recovers all 9505 bytes of this pairwise
instruction section with SHA-256
1a4701c011ba1ea1e80e036dc66b5f2489f78b28bc3f35e5f85014dab7ef8cb9,
matching the current file. That separate example establishes library retrieval;
the 298 Workflow example establishes selection through actual configured
resource contracts. The launcher path is corrected for future runs, without
altering the tested production modules or rerunning the completed native jobs.

`FILLED_PARENT_FORMS.json` retains the three actual direct parent forms and
their exact action/observation/gain counts. `FILLED_SCIENTIFIC_FORWARDING_FORM.json`
was extracted read-only from the final run's original runtime_forms table; it
retains the authenticated intermediate scientific form. The six partial,
no-hit, source-only and completion-only examples are retained in
`FILLED_PARTIAL_AND_ZERO_FORMS.json`. Complete original CASE.json files and
all native/Store artifacts remain under `final_checks/temporary/pytest/`.

`OWNERSHIP_AND_CONSUMERS.md` records the changed files, root-authorized receiver
filter extension and inspected ownership/state/communication/credit/continuation
path. `AUTHORITY_SHA256.txt` pins the original goal, mandatory instructions and
contracts. The original objective and all sixteen principles were reread
verbatim after native verification, then exact contract 008 before handoff.

Run groups overlap and are not additive coverage totals. Original failures and
their native artifacts remain unchanged.

## Qualification

This workload executes tiny local paired BLAST verification jobs and reuses the
existing native input/software identities. It installs nothing and performs no
database search, API call, HPC job or configured-model run. Five program binding
schemas are tested here; 294/296/297 retain their separate five-program native,
numerical and custody evidence. This full scientific numerical episode-path
example is BLASTX; it is not a claim of separately executing every program through
every full Workflow branch or of model-guided scientific reasoning.

Database identification, PSI/DELTA/RPS/VDB programs, API/HPC deployment and other
required tool families remain separate unfinished work. No literature grader,
annotation/W05 formula, controller policy, new scientific score, root execution
grant or model prompt redesign is included.
