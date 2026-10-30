# Exact proposed interface and decision/information trace

Proposal only. The first worksheet requires an ordinary two-field numerical
form, not another population operation. The bounded execution artifacts verify
the existing path separately; they do not execute this proposed new link format.

## Constructor contract

`a105_worksheet_template(section_requests, *, context_field="assessment_context")`
accepts only an ordered list of `{field, source, components}` objects. First
release is bounded to the two already implemented families below. Its source
roster is deliberately not every available literature namespace.

| source | assignment key | numerical role |
|---|---|---|
| literature_kinetic_cells | requested_kinetic_components | source kinetic parameter magnitude and native qualified contrasts |
| literature_kinetic_summary_precision_cells | requested_kinetic_summary_precision_components | source spread/counts and estimated random precision, including explicitly labelled scenarios |

`field` uses the existing CODE grammar and must not collide with the context
field. Each source appears once. `components` must exactly match the family's
existing component vocabulary, be unique and retain order. Unsupported families
raise `a105_worksheet_section_unimplemented`; the constructor does not silently
drop them or claim their scientific values are missing. This bound is an initial
implementation scope, not a scientific claim that only these assays exist.

Return exactly:

```
{
  submitted_form: closed ordinary schema with selected top-level aliases
                  and the exact constrained assessment context,
  assignment_rosters: object containing the selected existing roster keys,
  section_roles: ordered [{field, source, components, numerical_role}]
}
```

The schema/rosters/purpose are persisted in the existing original commission.
`section_roles` is host instructional metadata, not another numerical output or
fact family. No new source/provider/worksheet record, assignment marker,
capability flag or communication native-schema exception is proposed. The
submitted aliases expand through the already frozen numerical contracts.
Expanded original native schemas remain byte-equivalent; the constructor does
not add minItems, project a subset into the native schema, move its $defs or
change units. Exact component selection lives in the existing assignment.

`WORKSHEET_DECLARATION_PROPOSAL_001.json` is the concrete submitted two-family
schema. It is a proposal with source aliases, not an expanded current schema
fingerprint or an already admitted report. Context version codes identify the
form template outside scientific evidence; the model-facing renderer omits them.

## Constrained context: useful relationships, not scores

All objects are closed and all properties required. Arrays may be empty.
The context contains:

* `version`: exact template code.
* `assertion_refs`: actual existing hypothesis references, possibly empty while
  discovering a function. Hypotheses remain source-specific assertions, with
  the actual assayed subject retained; this adds no A101 target transfer.
* `quantity_links`: explicit relationships between exact selected quantities.
* `assertion_links`: explicit bearing of a requested numerical component on a
  declared assertion or named weakness, with supporting recorded references.

A quantity selector is exactly `{field, sheet_ref, component, quantity}`.
`field` is an enum of fields actually selected in this form, not an unrestricted
string; component is an enum drawn from the selected roster union and checked
against its field at semantic validation. `sheet_ref` is a source reference.
`quantity` is `cell_value`, `reported_spread`, or `reported_count`.
These subquantity codes refer only to values that the ORIGINAL selected native
row permits; they never authorize reading its private source sheet.

Quantity relationship meanings:

| code | meaning and evidence required |
|---|---|
| same_reported_parameter | Two permitted views point to the same original parameter report/number owner and compatible units, subject and endpoint. This does not establish the central statistic is an arithmetic mean. |
| same_reported_spread | The same source spread token, statistic and dimension occurs in both views. The SD is not twice-observed variability. |
| same_count_report | The same count report is reused with its repetition meaning. It does not equate physical n and statistical n. |
| conditional_precision_of_report | The scenario precision belongs to this summary's selected SD/count/model premises. It does not assert source-supported estimator ownership or source mean identity. |
| unresolved | Delivered information does not establish the proposed relationship. No equality, covariance or independence is inferred. |
| conflicting | Delivered facts/relationships conflict; preserve at least two distinct supporting records. |

An assertion link is exactly `{selector, assertion_ref, relation,
support_record_refs}`. `assertion_ref` is nullable and must be a member of
assertion_refs when nonnull. Codes `measures_asserted_endpoint`,
`addresses_named_weakness`, `does_not_establish_assertion`, `unknown`,
`conflicting` are constrained scientific interpretations, never numerical grades.
They are not an overall reliability/validity/relevance/attribution ladder.
Positive endpoint bearing does not certify molecular effect isolation. A named
weakness is recorded in its actual hypothesis/context/observation record;
the reader must answer that particular question using supplied evidence.

## Semantic validation, scientific unknowns and identity

`validate_a105_worksheet_links(form, schema, assignment, *, read_public_record)`
uses exact delivered rows, their original schema resource and already-possessed
public records. It must not call any repository.read on a child's full payload,
source.read, scientific reader/calculator, current source acquisition or model.

Required checks:

1. Detect this exact template through its context schema/version and verify the
   form's selected native-family field declarations are unchanged. Ordinary
   non-worksheet forms retain existing validation.
2. Resolve selectors to actually present `(field, sheet_ref, component)` rows.
   Check their assignment roster and subquantity allowance. A component code
   from the other field cannot substitute. Reject duplicate links and links to
   hidden/unrequested sheet numbers.
3. For native values/spread/count, public metadata references must already be
   carried by the requested side. Authenticate the available public anchor's
   source/artifact/span association through existing row custody, and compare
   it to the summary row's selected dependency_locations. Equal values alone
   cannot prove one report. Unit aliases such as the existing kinetic
   `uM_inverse_min_inverse` and summary `uM^-1min^-1` are the same dimensional
   code here; no new numerical conversion runs.
4. `same_reported_spread` additionally preserves statistic SD versus SEM and
   uncertainty units. `same_count_report` preserves physical/technical/unknown
   meaning without manufacturing independent preparations or statistical n.
5. `conditional_precision_of_report` requires a scenario row with its exact
   selected stipulations, the matching summary source report and retained
   variance meaning. It cannot label a scenario result as source-supported.
   Physical_measurement_id may stay null; neither sheet IDs nor new labels
   create a physical preparation identity.
6. Preserve uncertainty and contribution ownership. Source native parameter,
   source SD/count and scenario precision are dependent views of a source
   summary, not new independent assays. A same-report relationship is narrower
   than a fully established statistical estimator hierarchy.
7. Reference validation enforces actual record type/scope/possession; assertion
   relation constraints enforce allowed meanings. They do not deterministically
   prove a biological interpretation from an arbitrary supporting citation.
   The responsible episode still answers the concrete aspect question using
   the evidence. Scientific unsupported/unknown outcomes remain explicit.

Invalid references or unsupported positive link assertions return declared
`ContractError` codes (`a105_worksheet_selector_not_delivered`,
`a105_worksheet_subquantity_not_delivered`, `a105_worksheet_link_not_supported`,
`a105_worksheet_assertion_reference_invalid`,
`a105_worksheet_scenario_source_promotion`,
`a105_worksheet_duplicate_link`). Ordinary report repair retains all saved
numerical sections. No auto-retry, extra model report composer or scientific
completion gate is introduced. A link may be explicitly unresolved without
preventing admission of valid numerical partials.

## Concrete missing connections versus missing science

| Item | Status and required action |
|---|---|
| One ordinary form containing native and summary sections | Existing path; bounded controlled261 verifies it. No new aggregator. |
| Reusable selected worksheet constructor | Proposed convenience/contract function; currently unfinished. The child may already construct the equivalent ordinary form. |
| Cross-section same-report relationship validation | New narrow hook needed if this new link format is added. Existing generic reference validation alone does not check the relation. |
| Unified numerical/relationship display | Existing family renderers can display the values; proposed pure wrapper groups them and presents their shared identities without rehydrating private sheets. |
| AP source mean-precision assumptions | Missing source information: statistical n mapping, SD convention and IID/mean identities are not supplied merely by physical n=2. Do not repair them in code. |
| General summary variance -> physical covariance insertion | Unimplemented; not needed to compose this worksheet. A future requested arithmetic join needs exact estimator matching and all required covariance; estimated scalar variance is insufficient. |
| General effect isolation/relevance compilation | Not completed by this composition. Specific existing controlled/calibrated calculations retain their scope; unknown molecular attribution and physiological specificity remain unknown. |
| Nfn comparison258 | Other owner; no future namespace, operation or function assumed integrated. |

## TASK relevance issue and precise repair direction

Current literature_experimental_prompt._task unconditionally appends
RATE_REPLICATE_TASK, ASSAY_TASK, binding and binding-model TASKs, interaction-model
TASK, TRANSPORT_TASK, PERTURBATION_TASK, STRUCTURE_TASK, REACTION_TASK,
CONTEXT_TASK and PARTNER_TASK. Legacy fallback predicates can also inject rate
and kinetic comparison tasks. An AP summary-only assignment therefore receives
unrelated experiment instructions. Appending the proposed common TASK would
not resolve that problem.

Proposed helper, after separate template feedback:

```
selected_literature_task_sections(state, lookup_results=())
    -> ordered [(aspect_code, complete_task_text)]
```

Inputs are only assignment rosters, the original requested form's actual
registered families, actual owned-work markers, exact admitted row meanings,
explicit selected process instructions and actual operation/return lookup
information. An absent selection does not default to every method. Availability
of an operation alone is not a selected scientific aspect. The complete common
scientific TASK remains detailed. Every selected aspect's full substantive TASK
recurs after information lookup, failed action, history lookup and reconstruction.
The two real branches of an explicitly requested union operation contract must
still be distinguished and explained, without imposing both as an itinerary.

The AP native single-parameter job needs native source-reading instructions,
not just KINETIC_MODEL_TASK, whose four paragraphs describe a two-estimate
supplemental log model. This is a concrete prompt-template gap; it does not
invalidate the native numerator-only calculator. The full summary TASK remains
appropriate for its independent-estimator distinctions. Endpoint-only work
gets the complete endpoint TASK and no summary/model-contrast substitution.

Both `_task` builders (experimental child and reference-evidence parent),
lookup presentation, ordinary history rendering, return relevance and the
parent dispatch branch must use one reviewed relevant-selection result. The
parent retains its own full job; receiving a child's numerical rows adds terse
scientific STEERING and only relevant substantive instructions, never the
child's private task/history. No prompt code is changed in261.

## Boundary trace, STEERING and ordinary accounting

| Boundary | Decision and supplied information |
|---|---|
| Parent -> child | Parent selects the actual source question, allowed scope, full TASK and ordinary closed worksheet form plus exact component rosters. Children retain iterative source/read/repair choices. |
| Own action -> later child decision | Existing selected reader/calculator result provides only actual rows and failure meanings. TASK repeats in full; STEERING shows decision-relevant values/qualifications and own-action yield table. |
| Child closure -> parent | Original numerical facts and constrained interpretation fields form one ordinary saved object. Exact registered family validation/possession checks run. Parent receives only admitted rows and necessary relationship meanings. |
| Forwarding | Numerical families use their existing desired-order admitted intersection. Context links must be restricted to the forwarded selectors or explicitly reported unresolved; an orphan link cannot authorize hidden numbers. |
| Cold reconstruction | Original schema, descriptor, request, facts, admitted form, outcomes and section receipts are used. No re-reading original paper, recomputing SD/SE, model call, receive/write or current-code attestation supplies science. Frozen context is validated, not reinterpreted. |

Curt STEERING example (proposal, no fabricated observations):

| Requested evidence | Received value | Necessary qualification |
|---|---|---|
| AP D101A/E322Y pNPP catalytic efficiency | 0.000186 uM^-1 min^-1 | Source parameter and summary parameter are the same report. |
| Reported SD; independent preparations | 0.000006; 2 | SD; physical count, not established statistical n. |
| Source mean SE | unavailable | Estimator mapping/premises unresolved. |
| Stipulated mean SE | 4.242640687119285e-6 | Scenario random precision; systematic uncertainty unknown. |

The ordinary own-action-yield table separately reports actual category,
completed action count, total signed yield, expected next yield and uncertainty.
No worksheet total, score-count proxy or source row count replaces it. Two actual
selected population actions give two child own-action observations; their
reader/calculator internals add none. Their one returning child action gives
one parent observation under the existing projection, not one per section.
Rendering, identity checks, alias expansion and original report construction
add no observations. Repeated representation adds no scientific gain. The
configured estimator/controller remains unchanged.

Later verification should exercise only new concerns after coding: exact
constructor output, combined-family schema resource scope, supported versus
unresolved same-report links, unrequested/forged link rejection, forwarding
without orphan links, relevant full TASK recurrence at both boundaries and
first cold reconstruction of the new context without source/calculation IO.
Existing251/244 cohorts should not be rerun merely to manufacture a larger
count. This plan creates no original-source covariance quota or completion gate.

## Exact proposed later file ownership

No production edits are authorized by this plan. The reviewable later split is:

| Proposed owner | Exclusive files and responsibility |
|---|---|
| Fresh pure worksheet workload | NEW gene_annotation_episode/literature_a105_worksheet.py (constructor, closed context schema, narrow semantic validation); NEW gene_annotation_episode/literature_a105_worksheet_render.py (group existing rows and shared public identities); NEW gene_annotation_episode/literature_a105_worksheet_prompt.py (reviewed common and single-native TASK constants); NEW tests/test_literature_a105_worksheet.py; its own verification directory. |
| Fresh selected integration/presentation workload after that contract is reviewed | Existing literature_episodes.py (recognize exact template in validate_received_report and include new modules in as_record dependency fingerprint); literature_experimental_prompt.py and literature_reference_parent_prompt.py (relevant full TASK selection, worksheet rendering and constrained-link forwarding presentation); a NEW integration test file and its own verification directory. |

The pure link validator owns finite semantic checks; LiteratureEpisodes calls it
at its existing report-validation hook for the recognized template, including
saved reconstruction. Its output is a verdict, not a new fact source or action.
Initial link validation must not require successful scientific completion:
unknown links and incomplete requested rows remain valid partial information.

If a reusable TASK selector is factored out, it belongs in the pure worksheet
prompt module or one explicitly owned new literature-task helper; it must not
create another workflow or rewire shared runtime. The final release must choose
one location before coding, not have two owners edit the same prompts.

Existing communication.py, episode_contract_information.py,
literature_numerical_contracts.py and literature_numerical_return_presentation.py
already support these exact two registered families and their top-level aliases.
No change is currently identified there. Any unexpected necessary change returns
to exact-interface review; do not add a broad schema bypass. Frozen original
descriptors/contracts remain original; new dependency fingerprints apply only
to future selections, without migrating historical receipts.

No existing native/summary/endpoint/product/calibration/compiled calculator or
reader file is owned by the proposed assembly workload. Current comparison258
remains separately owned. No authority/progress file, test belonging to another
workload, shared runtime, method_loop, controller or W05 file is assigned.
