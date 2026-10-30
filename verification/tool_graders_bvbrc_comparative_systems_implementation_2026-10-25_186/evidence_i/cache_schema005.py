from pathlib import Path
p=Path('gene_annotation_episode/bvbrc_comparative_systems_returns.py')
s=p.read_text().replace('from copy import deepcopy\n','from copy import deepcopy\nfrom functools import lru_cache\n',1)
s=s.replace('def _expanded(name):','@lru_cache(maxsize=None)\ndef _expanded(name):')
s=s.replace('def _value_schema(kind):','@lru_cache(maxsize=None)\ndef _value_schema(kind):')
s=s.replace('def comparative_systems_fact_sources():','@lru_cache(maxsize=1)\ndef _fact_source_templates():',1)
pos=s.index('\ndef parent_form_schema(')
s=s[:pos]+'''\ndef comparative_systems_fact_sources():
    # Cache only immutable schema construction, never an authenticated fact or
    # a saved-state decision. Callers receive their own schema trees.
    return deepcopy(_fact_source_templates())

''' + s[pos:]
s=s.replace('schemas, seen = comparative_systems_fact_sources(), set()', 'schemas, seen = _fact_source_templates(), set()')
s=s.replace('values, descriptors = {}, comparative_systems_fact_sources()', 'values, descriptors = {}, _fact_source_templates()')
s=s.replace('descriptors = comparative_systems_fact_sources()', 'descriptors = _fact_source_templates()')
s=s.replace('schemas = comparative_systems_fact_sources()', 'schemas = _fact_source_templates()')
p.write_text(s)
