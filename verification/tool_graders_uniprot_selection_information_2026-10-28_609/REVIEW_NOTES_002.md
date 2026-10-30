# Additional source-review notes

This preserves the 001 draft and its artifact check record. It adds two limits
from the final inspection without installing or revising a prompt.

The recurring scientific TASK has another schema-display consumer:
`scientific_process_prompt._task`, lines 207-214, renders `requested_form` through
`_schema(rna_structure_return_schema_view(form), "return")`. That projection is
RNA-specific. If the scientific parent's own requested form contains a UniProt
selected return, this path can still expose the expanded UniProt contract.
Replacing this lookup's `result.text` alone does not repair that separate
requested-form presentation. Root must coordinate it with the selected-return
presentation work before claiming that the whole prompt keeps UniProt schemas
and witnesses internal. The parent's actual result meanings and full scientific
TASK must remain present when that display is repaired.

For an exact primary-accession selection, zero matched rows establishes
`record_selection_no_match` only if all native primary identities were
decidable. Missing or malformed native identities leave
`record_selection_indeterminate`. This is the same existing distinction as
Contract002 §5; the example does not turn lack of a returned row into a negative
biological finding. Template001's separate unknown/partial qualifications remain
necessary.

The same final review reconfirmed compact004 and the relevant selection and
forwarding meanings in Contract002, root handoff003 and host handoff005. Only
source/standard-library inspection was performed; the runtime paths above were
not executed.
