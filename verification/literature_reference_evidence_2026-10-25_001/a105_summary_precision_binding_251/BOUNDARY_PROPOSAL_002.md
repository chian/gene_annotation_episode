# Exact family admission and cold examples — plan only

Apply only after review/release. Native family name is exactly
`literature_kinetic_summary_precision_cells`. No prefix admission is proposed.

In `episode_contract_information._references`, the complete existing native
set becomes exactly:

```python
{'literature_gel_component_cells',
 'literature_controlled_response_component_cells',
 'literature_kinetic_summary_precision_cells'}
```

All existing depth/path, `set(node)=={'$ref'}`, string and
`startswith('#/$defs/')` checks remain verbatim. The family name itself is not
enough to admit an altered schema: `_closed` still calls validate_closed_schema.

In `communication._compile_closed_schema.check`, add this exact special case
before generic schema grammar checking:

```python
if source == 'literature_kinetic_summary_precision_cells':
    if depth != 1:
        raise ReportBoundaryError(
            f'{path}: fact bindings apply to whole top-level fields',
            code='invalid_schema')
    from .literature_kinetic_summary_precision_storage import SUMMARY_PRECISION_CELLS_SCHEMA_V1
    if (not _schema_cacheable(node)
            or json.dumps(node, sort_keys=True, allow_nan=False)
            != json.dumps(SUMMARY_PRECISION_CELLS_SCHEMA_V1,
                          sort_keys=True, allow_nan=False)):
        raise ReportBoundaryError(
            f'{path}: summary precision schema must match its registered source',
            code='invalid_schema')
    return
```

That constant is the exact detached RETURN_ROWS_SCHEMA001 JSON literal;
importing it invokes no pure248 schema/science factory. Existing _finite and
Draft202012 schema checks remain. Add the same exact family to the two existing
local-resource sets in communication._validate_form and
_validate_form_semantics.visit. The former validates the actual row payload
using Draft202012Validator(node), then replaces ONLY the validation copy's
parent field with `{}`. The latter sets resource=node and follows only its
local #/$defs paths before applying existing reference validation. This preserves
all original objects; source schemas/rows/contracts are never rewritten.

The row resource's `$defs` is an exact copy of sheet004 `$defs`; each named
cell schema is copied unmodified from its appropriate source/scenario group.
Therefore #/$defs/Cell, CellStates, SourceCellQualifications,
ScenarioCellQualifications, Unit_* and Value_* still resolve to the original
definitions. Do not attach those pointers directly to the parent form root.
The original full sheet schema remains a standalone separately saved resource.

## Concrete cold proof selections

`COLD_FORM_EXAMPLES_002.json` freezes literal and alias form objects with the
same exact selected row family, and their expected expanded schema. It includes
default-profile literal, default-profile alias and explicit-profile alias
cases. These are prospective proof inputs, not claims that unimplemented new
production paths already pass. The parent form has no model-authored fields.
The child assignment requests only `source_mean_standard_error`.

After a selected fixture run, a fresh process opens its existing store read-only,
recreates only the adapter/ordinary composer, and clears
communication._compiled_schema_content.cache_clear(). Before the FIRST compose,
poison reader/calculator/input-validator/extraction-validator/schema factories,
source IO and model/provider calls, receive, writes and current implementation
attestation. Each form must expand/authenticate from its own saved original
pending snapshot/declaration, authenticate saved original requested rows and
compose exactly that one row. The alias proof must not obtain new declarations
from today's registry. The literal proof must not bypass exact-family equality.
Validate the row standalone and resolve its own source/artifact references.
Compare unchanged original observations and original dependency receipt.

Required rejecting variations: local definition edited; named cell formula
changed; unit changed to count; unsupported external/local pointer; new family
name sharing a prefix; same family nested below a top-level field; broad extra
fields; alias referencing a newly available source absent from the original
snapshot. None may be accepted merely because a family x-source is present.

Default literal uses the original literal compile path. Default alias uses the
original bounded numerical-contract snapshot. Explicit-profile alias uses the
original contract-information snapshot. All three retain their own submitted
and expanded forms, source schema fingerprints and actual selected roster.
