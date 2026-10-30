# Receiver proposal 413/002: transport gap and admission status

This is additive feedback to `PROPOSAL_001.md`; no production or test code is
changed. The original proposal remains available for review.

## Exact operand-selection gap

The current action-generation transport does not solve the gap by keeping raw
typed records in host storage:

- `runtime._action_generation_schema` translates an `episode_child` assignment
  into a JSON-encoded string when `_json_episode_assignment` applies. The
  description says to preserve the exact assignment and embeds the complete
  original assignment schema. This is schema transport, not an alias resolver.
- `_json_tool_arguments` can select JSON-encoded tool arguments for composed
  schemas or the `json_object_contract_information_v1` transport. The host still
  validates the exact original argument schema. Simple `sequence.align`
  arguments retain their existing `query_ref` and `reference_ref` string fields.
- For the opted-in `operation_contract_information_v1` profile,
  `DecisionSource.exchange_decision` lets the model explicitly request
  `episode.operation_contract` or `episode.return_contract` inside the same
  decision. `Workflow.freeze_contract_information` retains the actual catalog,
  fact-source schemas and exchange schema; `contract_information_reply` uses
  those frozen declarations.
- `episode_contract_information.operation_contract_information` returns the
  operation meaning, exact input schema and rendered schema information.
  `return_contract_information` returns the permitted source's exact schema and
  meaning. Neither returns an actual received descriptor, chooses a reference,
  reads scientific data, or maps a biological label to an operand.
- `_SessionConnection._presentation` preserves those requested lookup replies
  while reconstructing the same full parent TASK. Internal JSON is still not
  automatic display authorization for arbitrary stored result records.

Thus an exact hidden sequence reference or saved-sheet descriptor remains needed
by the real next action. Hiding it from the STEERING text and returning only its
meaning does not make it selectable through the current schemas. This proposal
does **not** add an alias map, new operation, extra model call, transport, schema
exception or automatic work selection. The scientific result display can be
reviewed independently; autonomous follow-up commissioning from that display
cannot be claimed complete until this exact existing-consumer gap is resolved.

Original/later headings use only privately authenticated
`selector.acquisition` plus the original request / explicit selector parameters.
Calculator IDs never appear in the display. Stored numerical values, typed
returns and the parent's own recurring TASK stay unchanged.

## Additive status correction from root

After proposal001 was written, root reported that packet414's narrow typed
record admission correction passed its actual410 diagnostic and 58 checks.
Only the three mandated custody identities in the four exact protein fact fields
are exempted for **internal recorded returns**; model-input identity audits
remain strict. Root also reported 48 checks for packet411. These are root's
verification reports, not tests run by413.

The full410 check011 was still running when root sent that update. Therefore the
initial proposal's identity-audit blocker records the earlier finding; it is not
a claim that414 remains unfixed. The end-to-end scientific-parent prompt and
unresolved operand-selection seam remain separate from that admission repair.

## Concrete next boundaries after user feedback

1. Root supplies the four authenticated received groups at the existing parent
   context hook and joins only relevant request/selector metadata through the
   accepted existing authority port.
2. A presentation-only implementation consumes that supplied input, removes
   exact duplicate display copies and renders the approved STEERING tables.
   It leaves parent TASK construction, response schemas, credit and continuation
   untouched.
3. Root covers the existing provider's full/bootstrap/update/lookup/restoration
   paths and actual parent receipt path. Artifact reads and scientific
   recalculation remain excluded from formatting.
4. Exact follow-up operand selection is a separately unresolved consumer design;
   no new transport is inferred by this proposal.

No coding is authorized by this document before the user's template feedback.
