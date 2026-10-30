# Infernal authenticated return boundaries

Authority: reread the entire original goal at
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`
before work, and its objective and entire sixteen-principle block after substantial
source examination and before handoff. Do not replace that reset with a summary.
Read AGENTS.md and required original episode/communication design documents.

Own only `gene_annotation_episode/native_infernal_returns.py`, a new dedicated
`tests/test_native_infernal_returns.py`, and this verification directory. Root
owns ExecutionEpisodes and results receipts; 225 owns publication; 226 owns real
workflow tests. Do not edit their files or launch another scientific program.

Existing production hooks instantiate NativeInfernalReturns(owner) and call:
received_facts(context, schema), resolve_received(context, reference, namespace),
validate_received_report(context, form, schema), and
record_admission(context, form, schema, operation_key). Preserve those interfaces.
received_context(context) returns [{fact_source: source, facts: typed_rows}].

The current implementation handles the five execution_infernal_*_rows families.
It lacks legitimate execution_result_refs-only child forms. Complete that
boundary without granting numerical-row access from mere source possession.

Inputs are the existing original runtime commission, immutable child context,
runtime_actions, runtime_report_attempts, frozen runtime_forms, and validated
NativeInfernalResults receipts. Base EpisodeReturnRecords authenticates original
child relationships. Read its entire implementation and every affected consumer.

Required behavior:
- Authenticate actual immediate-child forms and original commission/closure.
- A results episode may return exactly its original requested typed numerical
  rows, or requested execution_result_refs, or completion only.
- A receiving scientific_process or annotation episode may receive/forward only
  what crossed its own child boundary. Preserve numerical values and explicit
  missing states; do not read a source into extra numerical rows.
- A source/reference-only form admits and resolves exactly the references
  actually returned by that Infernal child, but received_context contains no
  numerical groups and numerical identifiers remain unavailable.
- A completion-only form admits no scientific records or quantities.
- Generic execution_result_refs may belong to other providers. Do not interfere
  with their existing return implementations or claim their values as Infernal.
- Reject changed numbers, forged/unreceived identifiers, mismatched source,
  original scope/request/parent/child/return identities, and frozen-form changes.
- Preserve actually requested valid redelivery semantics and deduplicate exact
  received contributions without regrading, reacquiring or adding observations.

Outputs: existing closed typed family values; record_admission returns actual
received source/observation/model references only; resolve_received returns True
for an authenticated received reference/identifier, False for an invalid native
identifier, and None where this provider does not handle that namespace/reference.
Failures are precise ValueError/ContractError codes with the existing prefix.

No new episode, scientific score, monitoring loop, source store, model call,
unrestricted textual return, or credit change. Production selection stays with
the episode. Full native data stay retained; only requested data cross boundaries.

Coordinate with 226's real source-only/completion-only and forged-return tests.
Run focused meaningful checks under the existing 20 GiB RAM/4 GiB scratch local
runner, with no invented wall cap. Preserve actual failure/passing receipts and
state exactly which cases were executed. Report any missing root hook concretely.
