# Actual bound HMMER API operations

The launch parent commissions `launch_api` with the exact
`api_execution_assignment_v1`: resource ID, registered subject, service
`ebi_hmmer`, algorithm `phmmer` or `hmmscan`, database, parameters, page size,
constraints and any pinned instructions. These are assignment fields; each
operation below takes empty arguments and uses the original assignment.

| Callable operation | Actual behavior |
| --- | --- |
| `api.hmmer.databases` | One database metadata GET, retaining the actual response. |
| `api.hmmer.prepare` | Freeze the scoped query, submitted FASTA and request identities; no HTTP. |
| `api.hmmer.submit` | Commit submission intent, then one POST for the original prepared request. |
| `api.hmmer.status` | One status GET for the original UUID. |
| `api.hmmer.check_handoff` | One status GET and validation of the original job's monitoring/results handoff. |
| `api.hmmer.result` | In `results`, one GET of the page selected by that episode's original assignment. |

Read the bound catalog for the current role. No selected action polls, sleeps
or retries in a private loop. The API episode chooses its next operation in
`method_loop` using preceding outcomes and its configured yield controller.
The old `public.hmmer.*` execution/discovery tools have been removed.

The scoped subject, algorithm, database, parameters, page size, submitted FASTA
digest and parsed sequence digest remain fixed. FASTA bytes and sequence symbols
have different identities. A local provider job reference differs from the
remote UUID; retain both. A physical target identifies this exact submission.

Submission intent is saved before the single POST, and the response bytes are
saved before parsing its UUID. An uncertain submission never authorizes another
POST. Preserve its actual phase, diagnostic and partial records. Once the UUID
is known, a selected status observation or result request uses that UUID.
Infrastructure does not substitute a database or an approach.

Recursive monitoring uses the original handoff's exact target, with independent
observation custody. It does not add turns or credit to a closed launch.
Verified handoff immediately makes launch's expected future credit zero; the
physical job can continue. Execution/service facts remain distinct from
scientific interpretation and annotation support.
