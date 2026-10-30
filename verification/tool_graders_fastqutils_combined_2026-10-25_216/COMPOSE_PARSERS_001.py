"""Compose only sealed parser deliveries; never read active214 owned files."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
V = ROOT / 'verification'
BASE = V / 'tool_graders_fastqutils_cutadapt_verification_2026-10-25_208'
SRA = V / 'tool_graders_fastqutils_sra_implementation_2026-10-25_211'
CURRENT = V / 'tool_graders_fastqutils_samstat_implementation_2026-10-25_212'
LEGACY = V / 'tool_graders_fastqutils_samstat_legacy_2026-10-25_213'
OUT = HERE / 'candidate'
SHARED = {
    'gene_annotation_episode/bvbrc_fastqutils_schemas.json',
    'gene_annotation_episode/bvbrc_fastqutils_contracts.py',
    'gene_annotation_episode/bvbrc_fastqutils_metric_specs.py',
    'gene_annotation_episode/bvbrc_fastqutils_native.py',
    'gene_annotation_episode/bvbrc_fastqutils_bundle_adapter.py',
}
inputs = {}
changes = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, expected=None):
    raw = path.read_bytes()
    actual = sha(raw)
    assert expected is None or actual == expected, str(path)
    previous = inputs.setdefault(str(path.relative_to(ROOT)), actual)
    assert previous == actual, str(path)
    return raw


def load(path):
    return json.loads(read(path))


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def put(rel, raw):
    target = OUT / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def merge_schema(base, left, right, path=''):
    if left == right:
        return deepcopy(left)
    if left == base:
        return deepcopy(right)
    if right == base:
        return deepcopy(left)
    if type(base) is dict and type(left) is dict and type(right) is dict:
        assert set(base) <= set(left) and set(base) <= set(right), path
        result = {}
        for key in dict.fromkeys([*base, *left, *right]):
            at = path + '/' + key
            if key not in base:
                assert key not in left or key not in right or left[key] == right[key], at
                result[key] = deepcopy(left[key] if key in left else right[key])
            else:
                result[key] = merge_schema(base[key], left[key], right[key], at)
        return result
    if path.endswith('/enum') and all(type(v) is list for v in (base, left, right)):
        assert all(type(v) in (str, int, float, bool) or v is None for v in base + left + right), path
        assert set(base) <= set(left) and set(base) <= set(right), path
        merged = list(dict.fromkeys([*base, *left, *right]))
        changes.append(dict(path=path, base_count=len(base), sra_count=len(left),
                            samstat_count=len(right), combined_count=len(merged)))
        return merged
    raise AssertionError('Unresolved non-enum schema conflict at ' + path)


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def main():
    assert not OUT.exists(), 'Candidate already exists; do not overwrite a composition run.'
    base = load(BASE / 'source_before.json')
    sra = load(SRA / 'checks_001/source_before.json')
    current = load(CURRENT / 'COMMON_CONTRACT_MANIFEST_003.json')
    legacy = load(LEGACY / 'IMPLEMENTATION_HANDOFF_002.json')
    assert set(base) <= set(sra)
    for rel, expected in base.items():
        read(BASE / 'candidate' / rel, expected)
    for rel, expected in sra.items():
        put(rel, read(SRA / 'candidate' / rel, expected))
    for row in current['owned_files']:
        rel = row['path']
        raw = read(CURRENT / 'candidate' / rel, row['after_sha256'])
        if rel in SHARED:
            continue
        if rel in sra and sra[rel] != base.get(rel):
            assert sha(raw) == sra[rel], rel
        put(rel, raw)
    legacy_paths = dict(legacy['owned_code'])
    legacy_paths.update({row['fixture']: row['sha256'] for row in legacy['native_documents']})
    for rel, expected in legacy_paths.items():
        source = ROOT / rel
        target = source.relative_to(CURRENT / 'candidate')
        put(target, read(source, expected))
    for source in sorted((ROOT / legacy['fixture_directory']).rglob('*')):
        if source.is_file() and '__pycache__' not in source.parts:
            put(source.relative_to(CURRENT / 'candidate'), read(source))

    name = 'gene_annotation_episode/bvbrc_fastqutils_schemas.json'
    schema = merge_schema(load(BASE / 'candidate' / name), load(SRA / 'candidate' / name),
                          load(CURRENT / 'candidate' / name))
    put(name, (json.dumps(schema, indent=2, ensure_ascii=False) + '\n').encode())

    name = 'gene_annotation_episode/bvbrc_fastqutils_contracts.py'
    text = read(CURRENT / 'candidate' / name).decode()
    text = replace_once(text, "_FAILURES = frozenset(_DEFS['ContractFailure']['properties']['code']['enum'])",
        "# Both parser test generations name the same exact frozen208 grammar.\n"
        "_LEGACY_CUTADAPT_DEFS = _CUTADAPT_DEFS\n"
        "_FAILURES = frozenset(_DEFS['ContractFailure']['properties']['code']['enum'])")
    put(name, text.encode())

    name = 'gene_annotation_episode/bvbrc_fastqutils_metric_specs.py'
    text = read(SRA / 'candidate' / name).decode()
    text = replace_once(text, 'METRIC_ORDER = tuple(_METRICS)',
        'from .bvbrc_fastqutils_samstat_specs import SAMSTAT_METRICS, SAMSTAT_COMPONENTS\n\n'
        '_METRICS.update(SAMSTAT_METRICS)\n_COMPONENTS.update(SAMSTAT_COMPONENTS)\n\n'
        'METRIC_ORDER = tuple(_METRICS)')
    put(name, text.encode())

    name = 'gene_annotation_episode/bvbrc_fastqutils_native.py'
    text = read(SRA / 'candidate' / name).decode()
    text = replace_once(text, '    else:\n        parser = parse_unsupported_artifact',
        '    elif format_name in {"samstat_html", "samstat_html_2_2_3", "samstat_html_2_5_0", "samstat_bvbrc_error_html"}:\n'
        '        from .bvbrc_fastqutils_samstat_native import parse_samstat_html\n'
        '        parser = parse_samstat_html\n'
        '    else:\n        parser = parse_unsupported_artifact')
    put(name, text.encode())

    name = 'gene_annotation_episode/bvbrc_fastqutils_bundle_adapter.py'
    text = read(SRA / 'candidate' / name).decode()
    text = replace_once(text, '    "bvbrc_fastqutils_legacy_cutadapt_schemas.json",',
        '    "bvbrc_fastqutils_legacy_cutadapt_schemas.json",\n'
        '    "bvbrc_fastqutils_samstat_specs.py", "bvbrc_fastqutils_samstat_native.py",\n'
        '    "bvbrc_fastqutils_samstat_svg.py", "bvbrc_fastqutils_samstat_legacy.py",')
    put(name, text.encode())

    for generation in ('bvbrc_fastqutils_legacy_v2_schemas.json', 'bvbrc_fastqutils_legacy_cutadapt_schemas.json'):
        rel = 'gene_annotation_episode/' + generation
        assert (OUT / rel).read_bytes() == read(SRA / 'candidate' / rel)
    for rel in base:
        if rel.startswith('tests/'):
            assert sha((OUT / rel).read_bytes()) == base[rel], rel
    for source, expected in inputs.items():
        assert sha((ROOT / source).read_bytes()) == expected, source
    output = {str(p.relative_to(OUT)): sha(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file()}
    write_json(HERE / 'PARSER_INPUTS_001.json', inputs)
    write_json(HERE / 'PARSER_COMPOSITION_001.json', dict(
        status='parser_composition_created_calculator214_pending',
        base_paths=len(base), sra_paths=len(sra), current_owned=len(current['owned_files']),
        legacy_native_reports=len(legacy['native_documents']), merged_enum_locations=changes,
        original_tests_unchanged=True, exact198_and208_grammars_preserved=True,
        input_hashes_unchanged=True, output_paths=len(output),
        production_changed=False, tests_executed=False, scientific_calculator_pending=True))
    write_json(HERE / 'parser_source_before_001.json', output)
    print(json.dumps(dict(composed=True, output_paths=len(output), merged_enum_locations=len(changes),
                          production_changed=False, calculator214_pending=True), sort_keys=True))


if __name__ == '__main__':
    main()
