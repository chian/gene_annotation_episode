"""Check actual legacy compiler inputs against the presentation-only view."""
from pathlib import Path
import json
import sys
from copy import deepcopy

OUT = Path(__file__).resolve().parent
PIN = OUT.parent / 'a105_kinetic_review_198/pin_001'
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / 'tests')]
from gene_annotation_episode.runtime import _compile_form
from gene_annotation_episode.domain import obj
from gene_annotation_episode.literature_channel_storage import channel_cells_schema
from gene_annotation_episode.literature_compiled_assay_storage import compiled_assay_cells_schema
from gene_annotation_episode.literature_numerical_return_presentation import return_schema_view

checks = []
for name, factory in (('literature_channel_cells', channel_cells_schema),
                      ('literature_compiled_assay_cells', compiled_assay_cells_schema)):
    original = obj({'numbers': factory()})
    views = {'full_original': original, 'presentation_only': return_schema_view(original),
             'explicit_alias': obj({'numbers': {'$ref': 'episode-fact:' + name}})}
    for kind, schema in views.items():
        before = deepcopy(schema)
        try:
            actual = _compile_form(json.dumps(schema), {name: {'type': 'array', 'report_schema': factory()}})
            result = {'accepted': True, 'expanded_to_original': actual == original}
        except ValueError as error:
            result = {'accepted': False, 'error_type': type(error).__name__,
                      'error': str(error), 'diagnostic': getattr(error, 'diagnostic', None)}
        checks.append({'source': name, 'declaration': kind, **result, 'submitted_unchanged': schema == before})
result = {'checks': checks, 'scope': 'Direct actual compiler used by Workflow.expanded_contract_form when profile=None, on synthetic forms. This proves neither that every assembled legacy invocation fails nor that no alternate construction context exists. It establishes that a compact presentation cannot itself be submitted, and existing episode-fact alias requires the profile expansion path.'}
with (OUT / 'ROOT_CONSTRUCTION_PROBE_001.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result, indent=2))
