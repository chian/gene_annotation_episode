# 050: explain the existing native rate operand contract

Proposal only. No production module, test module, source parser, operation,
scientific TASK, numerical sheet, controller, pin or live-run state was changed.
The synthetic probes below examine caller usability, not experimental evidence.

## Finding and its limits

The current native rate route has important mechanical argument requirements
that its rendered callable schema does not explain:

1. Outer witness `start`/`end` are half-open UTF-8 **byte** positions in the
   selected source representation. Inner `number_start`/`number_end` are
   half-open Unicode **character** positions within the exact witness quote.
2. A source-defined unit's `definition.endpoint` must reuse the arm's endpoint
   witness exactly: source, representation, start, end and quote. Merely naming
   the same measured molecule in another span does not satisfy that contract.
3. The endpoint-entity span must be contained in that endpoint; the definition
   entity belongs in the selected definition clause. Equal strings at different
   occurrences cannot substitute for those positional relationships.
4. The selected bridge must include the complete supported unit definition,
   including any alternative endpoint branches. Selecting a phrase that stops
   before its time basis is rejected. The current finite grammar is narrower
   than arbitrary prose describing a unit.

These are established implementation requirements. They are not new scientific
selection instructions or permission to repair source text. Exact source bytes,
unit meanings and the investigator's experimental interpretation remain separate.

Code locations:

- `literature_assay_inputs.py:148` onward: exact witness byte validation and
  existing reversible quote-mismatch observation.
- `literature_partner_source_fields.py:96`: number-selector schema has numeric
  index constraints but no coordinate descriptions; its reader documents the
  byte/character distinction internally at line 207 onward.
- `literature_rate_native_inputs.py:59`: native argument schema reuses these
  bare witness/number structures, including defined units, in both arms.
- `literature_rate_native_inputs.py:114`: inner character slicing and conversion
  to original byte locations; line 200: exact endpoint identity and bridge
  boundary checks; line 254: plain unsupported `U/mg` retains a partial result.
- `literature_partner_defined_units.py:66`: defined-unit schema supplies field
  names without their containment/identity meanings; line 165 onward: ordered,
  source-bound clause/entity/quantity/time checks and explicit finite grammar.
- `literature_episodes.py:127`: actual native rate catalog entry exposes that
  schema. Its description says an endpoint-specific definition is needed but
  does not explain these positional requirements. Lines 518–550 retain exact
  error code/field; only quote mismatch gets structured detail.
- `scientific_process_prompt.py:84`: the shared schema renderer already displays
  JSON-schema `description` values. No renderer change is needed to display
  accurate operand descriptions.
- `literature_experimental_prompt.py:206` onward renders each actual tool's
  schema in recurring TASK; last outcome feedback is rendered as factual
  STEERING. Current scientific instructions say to select exact inputs but
  do not explain byte versus character positions or endpoint witness equality.

## Evidence actually produced

`reproduce_synthetic.py` ran through the current pure reader and schema renderer.
It wrote `SYNTHETIC_RECEIPT_001.json` and exited zero. All source bytes are invented;
there is no Store, run-database, provider-history, paper or network access.

- Invented rates 8 and 2 `U/mg` with an explicitly selected definition of one
  unit as 2 nmol of CompoundQ oxidized per minute yield 0.016 and 0.004
  `umol/min/mg`. This proves that the existing finite route can succeed.
- Selecting plain `U/mg` without the definition preserves raw 8 and 2 but makes
  their canonical values null with `source_defined_unit_definition_required`.
  That behavior is correct and must remain.
- An equal entity in a narrower endpoint witness is rejected with
  `defined_unit_endpoint_mismatch`; a clipped bridge with
  `defined_unit_bridge_boundary_required`; an equal entity at the wrong source
  occurrence with `defined_unit_containment_required`; byte indices used inside
  a quote containing μ with `literal_source_number_required`.
- Those four errors contain only code/field and `detail=null` at the pure reader.
  The actual rendered argument schema contains neither `UTF-8` nor `Unicode`,
  and no explanation of exact endpoint-witness reuse. The receipt lists every
  affected nested schema path with no description.

The parent's public `BOUNDARY_010.json` was inspected only as supplied bounded
feedback. It records a snapshot at 2026-10-26T16:18:01.169596Z: both original
process identities matched, both were present in state S, each had one native
population with ten null cells and the missing-definition reason. The 030
projection contains endpoint, containment, entity, clause, bridge and quote
errors. This is historical public feedback, not a fresh liveness check here.

The synthetic probes do **not** establish why those particular live selections
failed. No scientific source text, selected scientific arguments, paper packet,
private provider/model history or database was opened. Absence of instructions
is a verified usability gap; it is not proof of a faulty scientific unit parser.

## Proposed smallest implementation

Preserve all frozen readers and their scientific acceptance semantics. Add a
targeted schema-information module that obtains the existing native schema,
copies it, and supplies accurate `description` values at its known operand
nodes. It adds no fields, accepted values, defaults, numbers, source selectors,
parser routes, models or scoring components.

Prospective exclusive new files:

- `gene_annotation_episode/literature_native_rate_operand_information.py`
- `tests/test_literature_native_rate_operand_information.py`
- additive files in this 050 verification directory.

Prospective shared changes **only after 047 releases that file**:

- `gene_annotation_episode/literature_episodes.py`: use the annotated schema
  for the existing `literature.rate.source.populate` catalog entry, and include
  the new module bytes in the existing implementation fingerprint.
- An explicitly assigned integration test file, if parent selects one; no
  changes to 047's current tests without ownership transfer.

Do not edit the frozen native reader, defined-unit helper, assay reader, base044
storage or 045/046 modules to add documentation: their bytes are dependencies
of already reviewed contracts. Do not change the source operation's dispatch,
repository, cells, requested return projection or controller accounting. Other
tools keep their existing schemas until separately examined. No scientific TASK
constant, parent assignment, output contract or prompt renderer needs changing.

Proposed exact operand explanations include:

> Witness start/end: zero-based half-open UTF-8 byte positions in the selected
> original or text source representation. Quote is the exact decoded selected
> bytes; do not use character counts or alter markup/whitespace.

> Number start/end: zero-based half-open Unicode character positions inside
> this witness's exact quote. Select the complete printed numeric token. These
> are not artifact byte positions; the reader derives physical byte positions.

> Definition endpoint: copy the exact same witness selected as this arm's
> endpoint, including source, representation, offsets and quote. This identifies
> which measured endpoint the selected unit definition applies to.

> Endpoint entity: select its complete literal entity within the selected
> endpoint witness. Definition entity: select the corresponding literal entity
> within the selected clause. The current reader requires their normalized
> literal names to match; it does not infer chemical aliases or coupled products.

> Bridge: select the entire supported source unit-definition statement, with
> every alternative endpoint branch and its actual quantity/time basis. Current
> supported opening is “one unit was defined as” or “one unit was equivalent to”.
> Source wording is never rewritten to meet the parser. Unsupported wording
> remains an explicit reader limitation.

> Clause: select one complete amount–amount-unit–entity–per-time branch inside
> that bridge. Amount's physical numeric token, amount unit, definition entity
> and time unit must belong to this selected clause in their actual order.

The actual schema text must be concise enough to explain arguments without
dumping a source paper or scoring sheet. These are operation-operand meanings,
not a new general scientific TASK or a method-selection workflow.

## Verification if released

1. Strip only `description` keys recursively from the annotated schema and
   compare with the current native schema: every validation keyword, field,
   requiredness, enum, closed-object rule and branch must remain exact.
2. Check annotations cover both arms, their rate and uncertainty units/counts,
   every defined-unit field and each repeated witness/number selector. Build
   twice to prove no mutation of the underlying schema factory or prior result.
3. Validate the synthetic success and failure arguments with the schema and
   reader before/after annotation; scientific outcomes and errors must agree.
4. Render the actual selected catalog through the existing literature prompt.
   Required operand explanations must appear in TASK on initial and subsequent
   calls. Existing complete scientific TASK and curt outcome STEERING remain.
5. Confirm C7 still dispatches the same operation and typed return family, with
   one ordinary own action and no added model/source calls or observations.
6. Record exact file hashes, terminal targeted tests and the existing baseline
   comparisons. No broad reruns without an actual affected path.

Structured error enrichment is deferred here: the mapping from a generic
`unit.definition` error field back to an exact arm is not currently explicit,
and inspecting nominated arguments must not be presented as verified source
facts. Better initial operand information can be implemented without inventing
that diagnosis. Existing quote-mismatch detail stays unchanged.

## What still requires a concrete source case

A new source-backed investigation must establish which endpoint the published
unit actually defines, whether it is the measured reporter or asserted product,
whether source wording fits the finite grammar, and whether the selected spans
are scientifically appropriate. A missing definition cannot be supplied by
documentation. Unsupported wording may require another bounded reader design;
it does not authorize accepting aliases, generic U scales or model-written
scientific operands. Actual model-backed usable population remains unproved.

Old processes use immutable earlier pins. Do not hotpatch, restart, edit their
selections or reinterpret their saved null cells. Any later model demonstration
must identify the actually installed new capability and preserve original run
history. Routing from papers to components remains deferred; this work only
explains an existing component's actual input contract.

## Inspection record

Fully read the active goal attachment; root AGENTS and GOAL; EPISODE_STRUCTURE,
TIME_AWARE_ESTIMATION, TASK_AND_STEERING; full W04 amendment. The initial combined
output truncated TASK_AND_STEERING, so that complete file was reread separately.
Fully read native rate inputs (672 lines), defined-unit helper (336), assay
inputs (377), scalar source fields (340), rate storage (793), C7 (786 at read),
experimental prompt renderer (788 at read), shared scientific schema renderer
(466), source locator (169) and partner scientific TASK. Only the opening 130
rate-calculator and 90 experimental-contract lines were inspected; no full
review of those modules is claimed and no change is proposed there. Latest
039/040 human instructions were reread last before this proposal. No paper reset
was required because no paper or retained paper-specific packet was opened.
