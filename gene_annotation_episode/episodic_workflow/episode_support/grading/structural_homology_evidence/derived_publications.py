"""The native A102 sheets the Episode's own tools published as numerical inputs for credit: one work-table row per
published source, holding the sheet body and the use it is permitted for."""
from episode_runtime import TableDeclaration

DERIVED_PUBLICATIONS = TableDeclaration(name='a102_derived_publications', columns=('source_ref', 'body', 'permitted_use'),
    key=('source_ref',), record_refs=('source_ref',))
