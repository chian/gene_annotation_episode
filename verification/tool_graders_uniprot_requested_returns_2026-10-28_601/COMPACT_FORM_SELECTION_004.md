# Compact parent selection for UniProt typed returns

This additive implementation contract preserves Contract002's exact expanded
data shapes. It resolves the parent-input boundary before coding it. It changes
neither the user goal nor a saved declaration, form or observation.

The parent selects fields with the existing top-level fact shorthand plus one
explicit parameter:

```json
{
  "$ref": "episode-fact:uniprot_selected_returns",
  "x-uniprot-selection": {
    "version": "uniprot_return_selection_v1",
    "pages": []
  }
}
```

The example's empty pages list explicitly requests no UniProt facts. Real
commissions supply their exact page/record/field selections. No default fields,
source grants or sequence grants are inserted. The parent does not emit the
large expanded schema or its witness-field definitions.

## Exact changes owned by root

Only `gene_annotation_episode/episode_contract_information.py` and
`tests/test_uniprot_compact_selection.py` are owned by this increment. C still
owns the actual schema definitions and `communication.py` registration.

1. `_references` recognizes this two-key top-level object only for the exact
   `episode-fact:uniprot_selected_returns` reference. Every other reference keeps
   the existing one-key grammar. External/dynamic/nested references remain
   prohibited. The helper's existing `(field, source)` return shape is unchanged.
2. `expand_fact_form` first checks the child role and source against the supplied
   frozen fact map. For an explicit UniProt selection, require the supplied
   advertised base schema to match C's current empty-selection advertisement,
   then call C's pure `uniprot_selected_return_schema(selection)`. Continue using
   the existing closed-schema check and declaration structure. Record the
   selected expanded schema's existing fingerprint, not the empty base's.
3. `validate_saved_fact_form` uses the original submitted parameter and the
   actual saved expanded field. Require their selection fingerprints to agree
   before accepting the existing declaration/hash relationships. Do not invoke
   a source lookup or the current advertised fact map to reconstruct history.
4. Existing one-key fact shorthand, literal forms, allowed child-role checks,
   parent-chosen field names and non-UniProt sources keep their current behavior.

The pure builder import is limited to expansion of this explicitly selected
registered source. No workflow factory, source acquisition, episode, model
call, receipt mechanism or action observation is introduced. The older module
description will be corrected to describe this pure registered builder.

## Required checks

- Expand a real nonempty UniProt selector under an arbitrary parent field name;
  the exact expanded field equals C's builder output.
- Reject unavailable sources/roles, altered frozen base advertisements,
  unsupported siblings, malformed selectors and nested/external references.
- Validate the saved compact/expanded/declaration relationship; detect changed
  selection even when a caller tries to reuse declaration metadata.
- Keep saved reconstruction independent of current advertised source catalogs.
- Verify existing ordinary fact shorthand and literal-form tests still pass.
- Keep all returned forms/witnesses internal. This is not proof of a compliant
  model-facing presentation or downstream material-access binding.

The parent-facing description of this selection syntax is a separate information
message. Its concise text and the remaining UniProt result templates must be
printed for user feedback before their new presentation is implemented.
