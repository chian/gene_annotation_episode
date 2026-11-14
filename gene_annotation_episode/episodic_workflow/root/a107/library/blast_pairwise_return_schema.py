"""The original native BLAST paired-reference return declaration."""

def blast_pairwise_reference_source():
    return {'type': 'array', 'meaning': 'Native paired BLAST source, observation and reference records actually returned through this boundary. References alone do not deliver unrequested numerical rows.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'x-source': 'execution_blast_pairwise_result_refs'}}
