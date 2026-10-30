"""Compose the reviewed, immutable214 delivery into prepared216 only."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TARGET = HERE / 'candidate_003'
DELIVERY = ROOT / 'verification/tool_graders_fastqutils_samstat_calculation_2026-10-25_214'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


if __name__ == '__main__':
    handoff_path = DELIVERY / 'IMPLEMENTATION_HANDOFF_001.json'
    handoff = json.loads(handoff_path.read_bytes())
    source = ROOT / handoff['candidate']
    prepared = json.loads((HERE / 'prepared_source_before_003.json').read_bytes())
    for name, expected in prepared.items():
        assert sha((TARGET / name).read_bytes()) == expected, name
    changes = handoff['owned_changes']
    assert len(changes) == 18 and not handoff['outside_owned_changes']
    for item in changes:
        name = item['path']
        original = TARGET / name
        actual = sha(original.read_bytes()) if original.exists() else None
        assert actual == item['before_sha256'], ('merge_conflict', name)
        assert sha((source / name).read_bytes()) == item['after_sha256'], name
    for item in changes:
        dest = TARGET / item['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((source / item['path']).read_bytes())

    adapter = TARGET / 'gene_annotation_episode/bvbrc_fastqutils_bundle_adapter.py'
    text = replace_once(adapter.read_text(),
        '"bvbrc_fastqutils_samstat_svg.py", "bvbrc_fastqutils_samstat_legacy.py",',
        '"bvbrc_fastqutils_samstat_svg.py", "bvbrc_fastqutils_samstat_legacy.py",\n'
        '    "bvbrc_fastqutils_samstat_mapping.py",')
    adapter.write_text(text)
    assignment = next(n for n in ast.parse(text).body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == '_DEPENDENCIES' for t in n.targets))
    dependencies = ast.literal_eval(assignment.value)
    assert len(dependencies) == len(set(dependencies)) == 36
    for name in dependencies:
        assert adapter.with_name(name).is_file(), name

    test = TARGET / 'tests/test_bvbrc_fastqutils_provider.py'
    text = replace_once(test.read_text(),
        'assert len(provider._DEPENDENCIES) == 27 and provider.implementation_sha256() == expected.hexdigest()',
        'assert len(provider._DEPENDENCIES) == len(set(provider._DEPENDENCIES)) == 36\n'
        '    assert provider.implementation_sha256() == expected.hexdigest()')
    text = replace_once(text,
        "'bvbrc_fastqutils_legacy_v2_schemas.json'} <= set(provider._DEPENDENCIES)",
        "'bvbrc_fastqutils_legacy_v2_schemas.json', 'bvbrc_fastqutils_legacy_cutadapt_schemas.json',\n"
        "            'bvbrc_fastqutils_sra_native.py', 'bvbrc_fastqutils_sra_specs.py',\n"
        "            'bvbrc_fastqutils_json_tokens.py', 'bvbrc_fastqutils_samstat_specs.py',\n"
        "            'bvbrc_fastqutils_samstat_native.py', 'bvbrc_fastqutils_samstat_svg.py',\n"
        "            'bvbrc_fastqutils_samstat_legacy.py', 'bvbrc_fastqutils_samstat_mapping.py'} <= set(provider._DEPENDENCIES)")
    test.write_text(text)
    info = TARGET / 'gene_annotation_episode/bvbrc_fastqutils_tool_info.py'
    text = replace_once(info.read_text(), 'SAMstat2.2.3 legacy HTML and2.5.0 HTML',
                        'SAMstat 2.2.3 legacy HTML and 2.5.0 HTML')
    text = replace_once(text, 'MAPQ255 shares', 'MAPQ 255 shares')
    info.write_text(text)

    names = set(prepared) | {r['path'] for r in changes}
    after = {name: sha((TARGET / name).read_bytes()) for name in sorted(names)}
    record = dict(status='composed_not_yet_tested',
        source_handoff_sha256=sha(handoff_path.read_bytes()),
        delivery_paths=len(changes), total_tracked_paths=len(after),
        dependency_paths=list(dependencies), dependency_count=len(dependencies),
        root_owned_changes=['gene_annotation_episode/bvbrc_fastqutils_bundle_adapter.py',
            'tests/test_bvbrc_fastqutils_provider.py', 'gene_annotation_episode/bvbrc_fastqutils_tool_info.py'],
        production_changed=False, prior_candidate_changed=False,
        prior_test_exclusion_removed=True)
    for filename, value in [('CALCULATOR_COMPOSITION_003.json', record),
                            ('combined_source_before_003.json', after)]:
        with (HERE / filename).open('x') as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    print(json.dumps(record, sort_keys=True))
