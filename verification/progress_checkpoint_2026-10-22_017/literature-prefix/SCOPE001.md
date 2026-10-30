# One finite persisted commission prefix capture

This is the root-authorized read-only inspection of the already running
configured_literature_localization_001 caller. It does not launch, resume,
receive, admit, monitor through application ports, or control any work.

The capture opens only this run's workspace/state.sqlite3 and its saved
runtime-directory episode-execution/executions.sqlite. Both are opened with
SQLite URI mode=ro; immutable is forbidden for these active WAL databases.
One connection attaches the latter read-only, sets query_only, executes one
explicit BEGIN, performs finite SELECT/PRAGMA metadata reads, then rolls back
and explicitly closes in finally. The two databases have separately recorded
read windows and are not claimed to have an atomic cross-database snapshot.
There is one invocation and no retry, polling, backup, checkpoint or loop
waiting for a return. A missing return preserves a prefix and ends inspection.

Allowed reads: actual new-run journal ownership, original C1 intent/selection
and requested goal/scope/form, episode state/identity, selected-action metadata,
observation identities and scalar values, root-owned saved model-request
contexts/frames, root estimation/pending/wait contexts and root received forms,
receipt identity metadata, typed committed-record identity/kind/hash metadata,
durable commission lifecycle/execution identity, C3 envelope metadata and
admitted root forms. Child model requests/responses, reasoning bodies,
unreturned form contents, archive contents and private provider logs are not
exported. Execution tokens are never selected. No source/original/active006
database or provider/event file is opened. The script imports only stdlib.

Read-only filesystem inputs are the prior first-request proof, custody receipt
and committed-reference manifest, frozen007 source text for provenance and
source-pin verification, and the two current database paths' stat metadata.
Active database hashes are not stability assertions. Any ordinary reader
sidecar behavior is SQLite's active-WAL read behavior; no immutable shortcut
or source-zero-write claim is made for the active run.

Output is exclusively this new private /tmp directory. Raw saved root requests
and C1 contracts are copied under new names with original text hashes. Child
actions/observations are reduced to identities/scalars/enum fields; all complete
child model payloads remain in their original private journal. No application
imports, Store, Workflow, backend, capture, status, return_page, provider, model,
HTTP, native or control calls are permitted.

The result must distinguish: actual literature role selection; persisted worker
identity from current liveness; overlapping recorded parent/child intervals
from concurrency guesses; C3 publication from C4 admission and parent receipt;
saved frame observations from current recapture; useful later scientific use
from mere count/closure. Lack of a return or a later parent integration is an
explicit remaining limit, not a reason to capture again.
