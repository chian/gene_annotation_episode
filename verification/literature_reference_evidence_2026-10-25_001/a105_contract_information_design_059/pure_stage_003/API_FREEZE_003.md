#059 pure API freeze003 — before production coding

Only four new files are released: schema_information_text.py,
episode_contract_information.py and their two dedicated test modules. Existing
modules, defaults, runtime/provider/native wiring and scientific TASK remain
untouched. These helpers consume supplied data; they acquire no state/source,
invoke no factory/model and create no action or observation.

## Text codec

schema_information_text exports:

    schema_fingerprint(value) -> str
    render_schema_information(value, *, title: str) -> str
    parse_schema_information(text: str) -> JSON value
    SchemaInformationError(ValueError), with code and field attributes

The codec preserves finite JSON values, including bool/null root schemas and all
unknown keywords/literal data. Immutable Mapping/tuple host representations may
normalize to their JSON object/array equivalents; scalar bool/int/float/string/
null types remain exact. Cycles, nonfinite/non-JSON objects and nonstring object
keys are errors. Fingerprints use sorted-key finite canonical JSON with exact
scalar spelling; source dictionary insertion order remains in rendered tables.

Text is a strict complete named-definition document. Every scalar uses exact
quoted JSON-scalar spelling inside a typed table cell; this is not a serialized
schema/context envelope. Pipes, Unicode line separators, newlines and unpaired
surrogates have unambiguous escapes. Reference cells are distinct from literal
strings that happen to name a definition. Arrays retain positions/order; all
fields, constraints, descriptions and literal data remain. No external/local
schema URI is resolved. The parser rejects malformed, duplicate, cyclic,
unreachable or unknown definitions/fields and noncanonical documents.

## Pure information results

episode_contract_information exports:

    operation_contract_information(*, catalog, operation: str) -> outcome
    return_contract_information(*, facts_by_role, permitted_child_roles,
                                role: str, source: str) -> outcome
    expand_fact_form(submitted_schema_json: str, *, child_role: str,
                     facts_by_role, permitted_child_roles) -> expansion
    validate_saved_fact_form(*, child_role: str, submitted_schema_json: str,
                             expanded_schema, declaration) -> expanded schema
    ContractInformationError(ValueError), with code and field attributes

catalog is a caller-supplied frozen sequence of actual catalog rows with unique
nonempty names and explicit string description/input_schema; extra actual
catalog metadata is allowed but not exposed. Names and role/source keys are
semantic nonempty codes. facts_by_role is a caller-supplied frozen mapping from
role to actual fact-source metadata (type, meaning, report_schema). The declared
type must agree with that schema. These are structural checks, not proof of
installed capabilities or custody. Pure helpers never call mutable factories.

Every outcome has exactly:

    status, record_refs=[], changed_record_refs=[], result, feedback

Completed operation result has exactly:

    information_kind="operation_contract_information_v1",
    operation, meaning, input_schema, schema_sha256, text

Completed return result has exactly:

    information_kind="return_contract_information_v1",
    role, source, meaning, report_schema, schema_sha256, text

The meaning/schema are exact detached copies of the supplied declaration. Text
contains the full named-definition contract. Hash/schema fields are HOST payload
for future journal/reconstruction; the actual model text must use the text field.
No scientific values, source records, observations or score are returned.

An unavailable operation/role/source returns status invalid, result null and
feedback exactly {category:"decision_exchange", code:<finite code>}. Structural
malformation/duplicate catalog names raise ContractInformationError. There is no
fallback selection, capability expansion or mandatory-read flag.

## Compact forms and saved host declaration

Input submitted_schema_json is the ORIGINAL string, retained byte-for-byte as a
Unicode string. Strict parse_json_object supplies its JSON tree. An entire
top-level field may be exactly {$ref:"episode-fact:<source>"}. Only a source in
the explicitly permitted child's supplied fact map resolves. Clone its exact
report_schema, retain existing x-source if exactly matching or attach that exact
selector. Siblings, nested/external/unknown/disallowed refs and conflicting
source selectors are errors. No remote resolution or initial fact values exist.
All ordinary literal form fields/constraints remain. The unchanged closed form
validator checks the fully expanded result. Unsupported unresolved references
are not allowed through communication's closed guard.

expansion is exactly {expanded_schema, declaration}. declaration is exactly:

    version="episode_report_contract_declaration_v1",
    child_role,
    submitted_schema_json,
    expanded_schema_sha256,
    fact_references

fact_references is an ordered array, one per actually referenced top-level field:

    {field, source, schema_sha256, source_had_x_source:boolean}

schema_sha256 fingerprints the EXACT cloned original source schema, before
attaching x-source when necessary. source_had_x_source allows saved-only
validation to recover that original tree from the already saved expanded field,
without a current factory or duplicate schema payload. The exact expanded schema
is returned separately and must be frozen as the original typed child contract.
The original compact selection remains in the parent's existing selected action.

validate_saved_fact_form consumes ONLY these SAVED inputs and the original child
role. It checks exact submitted string/role, closed declaration shape, exact
expanded-schema fingerprint, reference/field roster, original-source fingerprints
and original compact-to-expanded relationship. It never accepts a current fact
map, registry or factory. It returns a detached validated saved expanded schema.
This validates relationships only: a forger who replaces every saved input can
construct another consistent record. Actual original C1/C4 identity/custody
authentication remains a required future integration boundary.

No partial compiler fallback, interpreted fact values or new form defaults are
introduced. Fully literal closed forms remain valid and have an empty reference
roster. Optional on-demand profile/transport markers, current catalog agreement,
strict actual decoder wiring, pending frames, native execution, C1/C4 and worker
forwarding are not installed by this pure stage.
