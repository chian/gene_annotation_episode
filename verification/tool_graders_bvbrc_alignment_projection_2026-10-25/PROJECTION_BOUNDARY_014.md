# Pure requested projection boundary

Implemented only `gene_annotation_episode/bvbrc_alignment_bundle_projection.py`
and its dedicated tests. Public entry points are exactly:

```python
project_requested_facts(*, sheet_set: dict | None, component_set: dict | None,
    missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...],
    requested_form: dict, parameters: dict, provider: str) -> dict

validate_projected_facts(facts: dict, *, sheet_set: dict | None,
    component_set: dict | None, missing_requirements: tuple[dict, ...],
    diagnostics: tuple[dict, ...], requested_form: dict, parameters: dict,
    provider: str) -> dict
```

Provider values are `msa` and `metacats`. The returned dictionary contains
exactly the requested field names. Its finite selectors cover all 15 selection
kinds and 14 outward source families, including all four XMFA routes.

The only production imports from the alignment implementation are public
contract helpers: `validate_parameters`, `validate_requested_form`,
`validate_selection`, `encode_reference`, `decode_reference`, `FACT_SCHEMAS`,
`MEASUREMENT_CATALOG`, and `DIAGNOSTIC_CODES`. No resolver private helper or
provider/scientific validator is used. JSON Schema checks, finite JSON checks,
canonical reference conversion and identity comparisons are not scientific
calculations.

The saved validator builds the exact finite selections again from the supplied
saved cells and compares the entire outward value. It checks original requests,
resolved slot/document identities, scoped analysis/population/category/group
membership, physical native row/field identity, original request kinds,
statistical basis, family membership, source correspondence and coordinate
identity. It does not recompute entropy, p-values, ratios, reference difference
classification, consensus, RF, coverage unions, rounding or source-coordinate
formulas. Deliberately changing a selected outward value fails equality even
when a supplied sheet remains structurally valid.

Authentication of original saved content, content hashes, adapter pins, owners,
commissions and actual execution-result references belongs to root's return
and host integration. This pure interface cannot detect a caller that replaces
both an authenticated saved scientific cell and its matching outward value
before supplying them; the host must supply authentic saved proof. It does not
prove the original scientific arithmetic again.

Original Parameters remain authoritative. A request omitted from saved
Components is unavailable only with its exact original-path quarantine
requirement. A request absent from the original Parameters is malformed.
Missing numerical operands return null and their supplied requirements;
explicit empty selectors return zero rows. Only `multiplicity: all_family`
copies every row of the explicitly named family. Requirement and reason
references consistently use `@requirements`; genuine source Store references
are preserved. Missing native values retain their native state. Native
observations have null method identity under accepted correction026;
calculated cells preserve their actual saved method.

The closed six-key outward XMFA measurement selection implements correction027
without changing commissioning. Only inapplicable selector keys become null.
All scientific symbol selectors and outward character fields are restricted to
one printable nonwhitespace ASCII character. Native protein detail labels are
internal and are not misrepresented as such characters.

`TEST_SYMBOL_COMPLETE_011.txt` records 111 passing checks in 12.11 seconds.
This adds 11 checks to the earlier 100-check receipt: invalid frequency-delta
symbols with available and unavailable operands, and a valid single-character
selector preserving an actual missing dependency. The production change is a
selector-shape check, not a formula or scientific-mode change.

The retained native MSA/MetaCATS and full XMFA provider examples are consumed
unchanged scientifically. Test helper commissioning and custody records are
explicitly synthetic. No new native job, live service request, episode, credit
observation, stopping rule, evidence-axis change or W05 calculation was made.
