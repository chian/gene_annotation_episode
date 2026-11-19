"""The work tables of the A102 structural tools: the structure bindings a source record stands for, the derived
publications a scoring reads back, and the saved result of each tool request."""
from episode_runtime import TableDeclaration

STRUCTURE_BINDINGS = TableDeclaration(name='a102_structure_bindings', columns=('source_ref', 'body'),
                                      key=('source_ref',), record_refs=('source_ref',))
DERIVED_PUBLICATIONS = TableDeclaration(name='a102_derived_publications',
                                        columns=('source_ref', 'body', 'permitted_use'),
                                        key=('source_ref',), record_refs=('source_ref',))
TOOL_RESULTS = TableDeclaration(name='a102_tool_results', columns=('request', 'result'), key=('request',))
