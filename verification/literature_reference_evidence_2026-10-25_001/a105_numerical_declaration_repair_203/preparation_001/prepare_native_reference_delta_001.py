"""Prepare only the bounded native-literal consumer patch for review."""
from pathlib import Path
import difflib
import hashlib
out=Path(__file__).resolve().parent
original=(out/'episode_contract_information.py').read_text()
assert hashlib.sha256(original.encode()).hexdigest()=='ac152800cfd851017150aedecbdd43b42dcfd6556803f5ecf998805ae653e242'
before='''def _references(schema):
    found = []
    for path, node in _schema_nodes(schema):'''
after='''def _references(schema):
    found = []
    # Existing exact native A105 literals own their local definition resources.
    # Only internal refs inside these complete top-level fact documents are
    # opaque here. _closed still requires their exact registered schema; all
    # aliases, external/dynamic refs and altered documents remain constrained.
    native = {field for field, node in schema.get('properties', {}).items()
        if isinstance(node, dict) and node.get('x-source') in {
            'literature_gel_component_cells', 'literature_controlled_response_component_cells'}}
    for path, node in _schema_nodes(schema):'''
assert original.count(before)==1
result=original.replace(before,after)
before='''        if not references:
            continue
        if (len(path) != 2'''
after='''        if not references:
            continue
        if (len(path) > 2 and path[0] == 'properties' and path[1] in native
                and set(node) == {'$ref'} and type(node['$ref']) is str
                and node['$ref'].startswith('#/$defs/')):
            continue
        if (len(path) != 2'''
assert result.count(before)==1
result=result.replace(before,after)
(out/'episode_contract_information.proposed.py').write_text(result)
(out/'episode_contract_information.unapplied.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),result.splitlines(True),fromfile='a/gene_annotation_episode/episode_contract_information.py',tofile='b/gene_annotation_episode/episode_contract_information.py')))
print('Prepared unapplied native reference delta; live consumer untouched.')
