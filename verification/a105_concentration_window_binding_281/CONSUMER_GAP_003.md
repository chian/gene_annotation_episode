# Exact native-schema registration gap

Production communication.py is readonly under this workload's brief and has
not been changed. Its existing native fact registration requires three narrow
integration additions for the proposed return resource:

1. `_compile_closed_schema.check`, adjacent to the measurement comparison branch
   at line197: recognize `literature_concentration_window_cells` only at depth1
   and require complete exact structured equality with the frozen constant
   `CONCENTRATION_WINDOW_CELLS_SCHEMA_V1`; return after that comparison.
2. `_validate_form` native field set around line511: include the new namespace
   so its local `$defs` resolve within the complete original fact document.
3. `_validate_form_semantics.visit` native resource set around line592: include
   the namespace so original reference annotations resolve through that same
   local resource rather than the enclosing form.

The general closed-form grammar rejects unrestricted native scientific strings
and internal `$defs` without this exact registered-document route. Registering
the family only in literature_numerical_contracts.py and
episode_contract_information.py cannot establish actual typed admission. The
existing comparison268 and summary-precision registrations demonstrate this
same bounded route. No generalized grammar exception, runtime, controller,
credit or interpretation policy change is proposed.

The parent was informed of this exact extra-path requirement. The owner did not
silently expand file ownership. Root release of these narrow portions (or a
root-owned change) remains required before production integration can proceed.
