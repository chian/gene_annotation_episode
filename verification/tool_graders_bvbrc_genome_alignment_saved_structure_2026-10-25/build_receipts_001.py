"""Reproduce the bounded saved-structure audit from retained native examples."""
import ast
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

import pytest
from test_genome_alignment_saved_structure import scientific_barrier, STRUCTURE
from test_bvbrc_genome_alignment_bundle_projection import synthetic_original_sheet, saved_arguments
from test_bvbrc_genome_alignment_bundle_resolution import measurement
from test_bvbrc_genome_alignment_returns import example, project
from gene_annotation_episode import bvbrc_genome_alignment_bundle_projection as projection
from gene_annotation_episode.execution_contracts import canonical, digest


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + '\n')


before = json.loads((OUTPUT / 'SOURCE_HASHES_BEFORE_001.json').read_text())
source_hashes, old_functions = {}, {}
for filename, original in before.items():
    raw = (ROOT / filename).read_bytes()
    source_hashes[filename] = hashlib.sha256(raw).hexdigest()
    functions = {node.name: hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
        for node in ast.parse(raw.decode()).body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    old_functions[filename] = {name: functions[name] == sha for name, sha in original['functions'].items()}
    assert all(old_functions[filename].values())
for filename in ('tests/test_genome_alignment_saved_structure.py',):
    source_hashes[filename] = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
save('SOURCE_HASHES_AFTER_001.json', source_hashes)
save('ORIGINAL_FUNCTIONS_UNCHANGED_001.json', old_functions)

sheet, original = synthetic_original_sheet()
components = sheet['components']
values = {row['kind']: row['measurement']['value'] for row in components['outcomes']}
selected = {'original': measurement('coverage', 'xmfa_original_coverage', 'coverage_fraction',
    member_number=1, original_member=original)}
args = saved_arguments(sheet, selected)
efacts = projection.project_genome_alignment_facts(**args)
fargs = example(sheet=sheet)
ffacts = project(fargs)
calls = Counter()
edges = Counter()


def trace(frame, event, arg):
    if event != 'call':
        return
    filename = Path(frame.f_code.co_filename)
    try:
        relative = filename.relative_to(ROOT / 'gene_annotation_episode')
    except ValueError:
        return
    callee = (str(relative), frame.f_code.co_name, frame.f_code.co_firstlineno)
    calls[callee] += 1
    caller = frame.f_back
    if caller is not None:
        source = Path(caller.f_code.co_filename)
        try:
            caller_path = str(source.relative_to(ROOT))
        except ValueError:
            caller_path = str(source)
        edges[(caller_path, caller.f_code.co_name, caller.f_lineno, *callee)] += 1


with pytest.MonkeyPatch.context() as monkeypatch:
    blocked_aliases = scientific_barrier(monkeypatch)
    sys.setprofile(trace)
    try:
        assert projection.project_genome_alignment_facts(**args) == efacts
        assert projection.validate_projected_facts(efacts['facts'], **args) == efacts['facts']
        assert projection.requested_projection_status(efacts['facts'], **args) == 'ok'
        assert project(fargs) == ffacts
    finally:
        sys.setprofile(None)

save('REPLAY_TRACE_001.json', {
    'qualification': 'Actual E project/validate/status and F pure saved functions. Retained native examples, synthetic source/task/original-map witnesses. F own/received custody paths are separately tested in pytest receipts.',
    'blocked_alias_count': len(blocked_aliases), 'blocked_aliases': blocked_aliases,
    'math_functions_blocked': ['log2', 'log', 'log10', 'isclose'],
    'native_document_representation_checks_retained': 'Native symbols, width and coordinate-span agreement are checked. These checks produce no saved scientific component. Scientific totals, selected-population counts, fractions, entropy and biological source comparisons remain blocked.',
    'calls': [dict(module=module, function=function, first_line=line, calls=count)
        for (module, function, line), count in sorted(calls.items())],
    'edges': [dict(caller_module=caller, caller_function=cf, caller_line=cl,
        callee_module=callee, callee_function=fn, callee_first_line=ln, calls=count)
        for (caller, cf, cl, callee, fn, ln), count in sorted(edges.items())],
})

v4, backbone, bbcols = (values[k] for k in ('mauve_v4_segments', 'mauve_backbone', 'mauve_bbcols'))
aligned, covered = values['xmfa_alignment'], values['xmfa_coverage']
fields = ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases')
save('FILLED_NATIVE_VALUES_001.json', {
    'qualification': 'Native measurements from retained upstream v4 and retained progressiveMauve sidecars/XMFA; explicit synthetic original-task/source/member/interval/original-map witnesses. No new native alignment, service task or model episode was run.',
    'saved_sheet_sha256': digest(sheet), 'saved_components_sha256': digest(components),
    'native_artifacts': [p['artifact'] for p in sheet['data']['parsed_artifacts']],
    'outcomes': [{k: row[k] for k in ('request_id', 'request_index', 'kind', 'state')} for row in components['outcomes']],
    'v4': {'coverage': [{**{k: row[k] for k in ('member', 'known_union_intervals', 'complement_intervals')},
        'cells': {k: row[k] for k in (*fields, 'denominator_bases', 'coverage_fraction', 'complement_bases')}} for row in v4['coverage']],
        'gapped_identity': v4['pair_segments'][2]['counts']['identity_fraction'],
        'coordinate_only_pair_states': [row['state'] for row in v4['pair_segments']]},
    'backbone': [{**{k: row[k] for k in ('member', 'known_union_intervals', 'complement_intervals')},
        'cells': {k: row[k] for k in (*fields, 'denominator_bases', 'coverage_fraction')}} for row in backbone['coverage']],
    'bbcols': bbcols['intervals'],
    'xmfa_pair': aligned['blocks'][0]['pairs'][0],
    'xmfa_first_site': aligned['blocks'][0]['sites'][0],
    'xmfa_coverage': [{**{k: row[k] for k in ('member_number', 'known_union_intervals', 'complement_intervals')},
        'cells': {k: row[k] for k in (*fields, 'source_length', 'selected_coverage_fraction')},
        'original_coverage': row['original_coverage']} for row in covered['members']],
    'coordinates': values['xmfa_coordinates']['cells'],
    'inverse_coordinates': values['xmfa_inverse_coordinates']['queries'],
})

validator_names = [validator.__name__ for validator in STRUCTURE]
validator_names += ['validate_mauve_v4_components', 'validate_mauve_backbone_components',
    'validate_mauve_bbcols_components', 'validate_xmfa_alignment_components', 'validate_xmfa_coverage_components']
references = []
for path in sorted((ROOT / 'gene_annotation_episode').glob('*.py')):
    source = path.read_text()
    for lineno, line in enumerate(source.splitlines(), 1):
        for name in validator_names:
            if name in line:
                references.append({'path': str(path.relative_to(ROOT)), 'line': lineno, 'validator': name, 'source': line.strip()})
save('VALIDATOR_REVERSE_REFERENCES_001.json', references)
print(json.dumps({'blocked_scientific_aliases': len(blocked_aliases),
    'unchanged_original_functions': sum(len(rows) for rows in old_functions.values()),
    'retained_native_artifacts': len(sheet['data']['parsed_artifacts']),
    'request_families': len(components['outcomes']), 'source_hashes': source_hashes}, indent=2))
