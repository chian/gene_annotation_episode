# Additive v3 partial-results correction002

This supplements the initial069 proposal before any implementation release.
The v2 request/output and actual068 calculator remain unchanged. Root required
unrelated usable numerical components to survive active companion reconciliation,
and explicitly required source-supported JOINT assignments rather than an
unsupported Cartesian product. No scientific reconciliation policy is adopted.

The final proposed v3 request adds TWO closed fields to the complete061 base
(plus its distinct v3 version): companion_readings and
joint_reading_assignments. The latter is an array of exactly:

```
{
  assignment: {protein_condition1: null|string,
               empty_condition1: null|string,
               protein_condition0: null|string,
               empty_condition0: null|string},
  admissibility: {value: compatible|unknown|conflicting, witnesses: Witness[]}
}
```

Null denotes the original primary reading; a string denotes an actual unique
companion reading_key for THAT primary_role. No numbers can be nominated here.
Duplicate assignment maps, unknown keys, keys for another role and incomplete
role maps are rejected. Compatible requires actual source witnesses, meaningful
same-owner/context relationships and actual jointly usable source/model scope.
Conflicting requires distinct source witnesses. Unknown remains unknown.
Compatibility is simultaneous applicability of those source representations;
it asserts neither statistical independence nor preferred source authority.

Only explicitly nominated, authenticated, compatible JOINT assignments populate
alternative_inputs. Include every such assignment; do not form a Cartesian
product, choose favorable combinations or treat unknown compatibility as known.
Source-linked alternatives may be coupled by the same graph interpretation,
normalization, revision or covariance/model scope. Retain that restriction.
The reader additionally validates that a compatible nomination is meaningful;
model-selected labels alone do not establish this relationship. Source-invalid
FULL C still cannot be rescued in any assignment. Conditional alternative inputs
use each nominated ACTUAL reading and its actual science, units, origin and C.

Final v3 extraction additionally has:

- partial_calculation_inputs: null or exact actual068 OwnerInputs;
- alternative_inputs: array of exactly {reading_assignment,calculation_inputs};
- calculation_inputs: exact actual068 OwnerInputs only for a ready reconciled
  projection; null for unresolved_active_reconciliation.

With unresolved ACTIVE reading choice, partial_calculation_inputs preserves
unaffected science and numeric operands. An actually unresolved single scalar
is projected into that role as a NONNUMERIC ambiguous reading group:
value=null, threshold=null, relation=none, status=ambiguous,
digitization_interval=null. Retain its actual known compatible unit where
established, original effective scientific meanings and physical owner, with
approximate=true if any retained actual alternative is approximate/graphical.
Use graph_derived origin if actual graphical alternatives participate; otherwise
retain the actual reported/synthetic origin. This classifies the unresolved
source representation; it invents neither a numeric graph observation nor a
synthetic measurement. Original primary/companion records retain their individual
origins and numeric values unchanged. Mixed synthetic/reported source provenance
requires its existing explicit source-scope qualification, never relabeling a
real measurement synthetic for convenience.

The nonnull group source_observation_id must be reconstructed from actual
retained authenticated reading/nominations, with the host identity declaration:

```
identity("controlled_active_reading_group", {
  primary_role,
  primary_reading_id,
  companions: [{reading_key, reading_id}, ...],
  scientific_owner_id
})
```

Use original nomination order, and actual reader-generated IDs; IDs identify the
retained reading GROUP, not a new physical observation or an extra experiment.
No self-authored arbitrary string grants custody. If the entire group is
unavailable and no authenticated reading/nominating identity exists, use the
actual missing-input semantics and null source identity, never invent a group
success. A scientific owner/context/applicability disagreement must use its
actual unknown/conflicting scientific projection; it cannot be hidden as merely
ambiguous numbers or erased by copying a favorable primary meaning.

This mask supplies no dummy number. It explicitly states that no single active
numeric reading has yet been chosen. Actual068 accepts it and deterministically
preserves raw values and local comparisons whose dependencies do not include
that unresolved role. The extraction's reconciliation state distinguishes
source-disagreement/contradictory domains, actual scientific disagreement and an
unimplemented reading model. The calculator's narrower ambiguous-input reason
is never presented as a finding that each original source token was unreadable.

The separate closed conditional-population proposal has exactly version,
projection_status, final_sheet, partial_sheet, unresolved_roles,
component_dependencies, alternatives, unaffected_cells and conditional_cells.
The source reader calls no calculator. A subsequent native consumer invokes068
once for the actual partial input and once per supported joint alternative,
retains every original output, and adds no runtime observation for these helpers.

When unresolved, final_sheet=null. partial_sheet is the actual068 output from
the nonnumeric ambiguity projection. alternatives each contain the exact reading
assignment and its actual068 sheet; this does not install a final scientific
reading model. `component_dependencies` has all twelve exact component keys,
each with original scientific_roles, numeric_roles, covariance_owner_ids and
model_active_roles. It is reconstructed from actual source meanings, original
owner coefficients and068 dependencies, never from equal floats.

An unaffected cell requires that its scientific AND numeric dependencies exclude
the unresolved scientific/reading scope, that its complete CELL_FIELDS and
qualifications equal the original partial sheet, and that its full meaning and
dependencies agree across every admissible joint alternative when any exist.
Compare complete cells and dependencies, not merely the numerical value. The
controlled contrast, source profile and signed index are never promoted as a
final reconciled result while active reconciliation is unresolved. Every other
cell preserves its own original precision, approximation, model and source
qualifications. conditional_cells retains each nonshared actual cell with its
alternative_index. Do not manufacture independence or sum alternative sheets.

In the constructed A example, the partial sheet keeps raw B=.004, raw C=.008,
raw graphical B=.00405[.00395,.00415] and condition0 local
.00395[.00385,.00405] umol/min. Raw A/local1/final contrast remain unavailable
in the partial sheet because their active reading choice is unresolved. Native
source rows STILL preserve A10 and its graph10.05[9.95,10.15], plus their real
reported spread/count/C. When the two JOINT assignments are explicitly supported,
their conditional e cells are .002 and .00205[.00195,.00215] umol/min. Neither is
chosen as final, and no conditional S/B becomes final model support. If joint
admissibility remains unknown, there are NO alternative sheet calculations;
the same unaffected raw/local partial cells still survive.

The constructed fixtures execute accepted068 on hand projections and validate
the closed population shape. HAND group-reading IDs are explicitly labeled
engineering placeholders in these fixtures, not reader-generated identities or
source custody. The future reader must generate the specified actual identity.
No new reader, source interpretation model, native partial projection or typed
admission is implemented here. Native integration must expose both unchanged
partial cells and requested source-native alternatives through separately
declared closed fact views; a mere null final sheet is insufficient completion.
The actual active scientific reconciliation/model remains REQUIRED unfinished
work, together with source/native/typed execution and reconstruction.
