# Amount027 repository and ordinary consumer proposal

Engineering proposal only. Shared files remain owned by024. AMOUNT_TASK remains
draft/unwired pending its exact user-facing presentation and running feedback.
The initial027 numerical core is separate from the unfinished reader/repository.

## Proposed selected operation and immutable record

New module `literature_amount_storage.py`, class `LiteratureAmountRepository`:

- provider `literature.a105.amount_population`
- record_version `literature_amount_population_record_v1`
- operations_table `literature_amount_operations`
- received_table `literature_amount_received`
- `populate(context, arguments, operation_key)`
- `read(sheet_ref)`
- `project_cells(sheet_refs, *, permitted_record_refs, components=None)`
- `validate_returned_values(cells, *, permitted_record_refs)`
- `receive_cells(context, cells, operation_key)`
- `received_cells(context)`
- `amount_cells_schema()` returning the closed `literature_amount_cells` source
  projection.

The selected C7 operation is `literature.amount.populate` with the exact
`amount_arguments_schema()` contract. It reads only sources already received
by that episode and in its actual scope. Every selected witness source and the
covariance source receives this authorization; existence in shared Store is
insufficient. A page/reading assignment additionally constrains direct operands
to the assigned source or its retained descendants. Scoped source provenance
closure can retain ancestors; it does not grant receipt of their source bytes.

The operation signature includes the unmodified arguments, run/episode owner
and scope. Same-key/different-work reuse is rejected. Replay rechecks actual
source access/ancestry and returns the original committed outcome; it does not
reinterpret the paper, reread numbers or recalculate cells.

Proposed saved payload, with every field required:

```
version
input_source_ref
input_artifact_ref
direct_input_source_refs
input_source_refs
selection
extraction
sheet
quantity_bindings
experimental_bindings
```

`selection` is the original closed model-selected operand object, unchanged.
`extraction` retains verified witnesses, original numerical tokens/units,
converted values, lexical bounds/approximation, episode meanings, physical and
source-token owner identities, uncertainty statements and full covariance
source ownership. `sheet` is the original deterministic output, not a replacement
for the selected operands. `quantity_bindings` records exactly the two roles;
`experimental_bindings` records experiment, intended change and covariance
source references (each nullable where unknown).

The canonical payload, request and original outcome are committed atomically
with their immutable ordinary source/reference/context/term records. Bindings
must identify actual source assertions; a 'reference' record does not assert
that the named molecule caused a measured endpoint. New source records retain
the exact direct inputs and permitted ancestry. Publication adds no separate
controller observation or source-interpretation action.

## Proposed exact closed return row

Every row property below is required. Null is a declared unknown/unavailable
value, never an omitted property. No unrestricted findings string is added.

| Row property | Type / allowed meaning |
| --- | --- |
| sheet_ref | source reference |
| evidence_source_ref | source reference |
| experiment_ref | nullable reference |
| intended_change_ref | nullable reference |
| covariance_source_ref | nullable source reference |
| component | one of the twelve COMPONENTS |
| value | finite number or null |
| threshold | finite number or null; individual censored quantity only |
| bound | none, lt, le, gt, ge |
| unit | mg/ml, uM, mg/ml_squared, uM_squared, dimensionless, or null |
| status | populated or unavailable |
| origin | reported, derived or synthetic |
| unavailable_reason | exact member of the reader/calculator reason union or null |
| conditional_on | unique closed condition-code array |
| approximate | boolean; source approximation retained |
| evaluation_scope | constant source_amount_comparison |
| comparison_kind | exact COMPARISON_KINDS member |
| pair_relationship | supported, unknown or conflicting |
| stock_relationship | same, different, not_applicable, unknown or conflicting |
| variance_status | known, estimated or unknown |
| covariance_origin | reported, derived, synthetic, or null |
| numerator | closed quantity metadata object below |
| denominator | closed quantity metadata object below |
| input_measurement_refs | unique array of reference identities of the component's actual operands |
| mass_factor_applied_to_rate | constant false for this version |

`mg/ml_squared` denotes `(mg/ml)^2`, not mg/ml². A later notation change must
be explicit and versioned before a published return is pinned.

Each required `numerator`/`denominator` metadata object has required fields:

```
subject_ref: nullable reference
construct_ref: nullable reference
preparation_ref: nullable reference
stock_ref: nullable reference
method_ref: nullable reference
reported_basis_ref: nullable reference
condition_ref: nullable context
measurement_ref: nullable reference
physical_observation_ref: nullable reference
amount_role: exact AMOUNT_ROLES member
amount_kind: exact AMOUNT_KINDS member
basis_status: supported | unknown | conflicting
qualification: reported_point | source_qualified_approximate | unknown | conflicting
approximate: boolean
reported_uncertainty_kind: sd | sem | ci | untyped | unreported | unknown | conflicting
reported_uncertainty_ref: nullable reference
```

Unknown proper names do not independently veto a scientifically supported pair.
For example, a witnessed same-stock relationship can identify the relevant
preparation without inventing a searchable name. The quantity metadata gives
the scientific roles and limitations of the requested cell; it does not expose
unrequested individual numerical amounts or private child findings.

For an individual amount cell, input_measurement_refs contains that role's
measurement only. Paired arithmetic references both operands. Propagated
variance/standard uncertainty reference both operands and the covariance source
through its separately typed field. The conditional factor shares the
reciprocal's operands and is not an independent contribution.

Conditions are exactly source_role_and_pair_interpretations,
linear_covariance_propagation, first_order_covariance_propagation and
same_stock_rate_with_total_mass_denominator_required_before_application. The
mass-factor cell alone retains the last condition. Full covariance ownership
and physical identity hashes remain in saved host records, outside prompt text.

## Saved-only reconstruction and admission

`read` verifies selected-output membership in the exact run's operations table,
request/selection equality, source/provider/version/artifact associations,
direct/provenance rosters, and the stored original outcome's cells. It verifies
saved extraction/selection correspondence and published quantity bindings
without opening scientific source bytes or recalculating the numbers.

`project_cells` copies selected original saved cells and their scientific
meanings only after receipt authorization. It must not silently accept an
unrelated provider/version, widen requested components, or compute fresh
numbers during return construction. Exact returned numerical values and all
meaningful field associations are checked against the saved projection.
Duplicate `(sheet_ref, component)` pairs are rejected. Forged bindings or changed
unavailable reasons fail admission as well as changed values.

`receive_cells` persists only the already-admitted requested subset for the
receiving episode. Redelivery has the same identity and cannot manufacture a
new cell or observation. Forwarding uses this received subset, not a full
private child sheet. `received_cells` preserves original first receipt order
and deduplicates the same cell identity; it never upgrades conflicting data.

## Shared changes after explicit ownership release

1. `episode_services.py`: one lazy literature_amount_repository accessor using
   the actual Store and run_id. It selects no work and owns no new loop.
2. `literature_episodes.py`: operation catalog/dispatch; required-source ancestry
   checks; requested_amount_components; implementation hashing of all new amount
   modules; fact schema and population route; exact saved return validation;
   source custody, requested-subset admission and ordinary forwarding.
3. `literature_experimental_prompt.py`: import/insert the reviewed AMOUNT_TASK
   without replacing full TASK; retain requested_amount_components; render
   selected direct and received amount cells with both quantities' scientific
   meanings and approximation/uncertainty. Exclude host identity bookkeeping and
   private/unrequested quantities. Existing scientific parent TASK remains its
   own; admitted child amount facts become concise STEERING.

All selected work stays in existing LiteratureEpisodes/shared method_loop. No
per-axis episode, report composer, mandatory itinerary, event, internal action,
credit policy or controller change is proposed. The caller's existing explicit
rate_population experimental binding can expose this population family; its
historical name does not create an additional score or new sheet.

## Required connected checks

New amount-specific tests should establish actual025 source operands and scoped
covariance ownership, incompatible/missing bases, stock relationships without
public names, limits/approximation, ratios above one and shared physical owners.
Repository tests must cover selected-output membership, custody on replay,
saved-only reconstruction with scientific-source reads forbidden, exact subset
copy/admission, changed values/roles/units/bindings rejected, and redelivery.
An ordinary controlled episode consumer must execute the selected operation,
return requested closed amount rows to its scientific parent and preserve those
facts in the parent's next steering. The ordinary action/observation count must
agree; it must not count parsing, calculation, saving or rendering separately.
No configured-model inference or actual independent replication is established
by those engineering fixtures.

## Subsequent parent correction

Before any storage publication, use the unambiguous variance unit codes
`(mg/ml)^2` and `(uM)^2`. These supersede the draft `mg/ml_squared` and
`uM_squared` codes in the row table above. The numerical core and focused tests
now use the parenthesized units. No old saved record or published contract was
changed; the storage projection is still a proposal.
