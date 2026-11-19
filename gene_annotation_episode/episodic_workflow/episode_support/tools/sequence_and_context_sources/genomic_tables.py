"""The work tables of the genomic tools: the locus bindings a source record stands for, and the saved result of
each tool request."""
from episode_runtime import TableDeclaration

BINDINGS = TableDeclaration(name='a103_bindings', columns=('source_ref', 'body'), key=('source_ref',),
                            record_refs=('source_ref',))
RESULTS = TableDeclaration(name='a103_tool_results', columns=('request', 'result'), key=('request',))
