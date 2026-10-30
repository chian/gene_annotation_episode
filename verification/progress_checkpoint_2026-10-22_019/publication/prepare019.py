"""Author an unadopted progress019 candidate using regular saved evidence only."""
from pathlib import Path
import ast
import hashlib
import json
import os
import re
import stat

HERE = Path(__file__).resolve().parent
REPO = Path('/home/chia/repos/gene_annotation_episode')
OLD = REPO / 'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_018.md'
OLD_SHA = 'fb3845dfda7a6852ec755afc0cf8df6b859c0941c517fab72b57c9248a7f4834'
PRIOR = REPO / 'verification/progress_checkpoint_2026-10-22_018'
PRIOR_MANIFEST_SHA = '4925b94b70693753e9ad0364aee43c5cc74dc51a2632aaebaac915ac011cf488'
FIXTURE_PARTS = {'fixtures', 'raw-fixtures', 'pytest-fixtures', 'preserved-fixtures'}
BUNDLES = [
    ('direct-contract', '/tmp/direct-hmmer-timing-contract-R-20261022-hci0ry6b', 'MANIFEST_FINAL001.json', 'da577446cfa0d252edb3037b437f49a9d19ff6301e2b1c5229208308509da781', 'all'),
    ('static-source008', '/tmp/direct-hmmer-008-static-snapshot-20261022-001-zoe7igsh', 'MANIFEST001.json', 'b0b92291abf520876f97524e887d8a5b4b242498183a492ed84195752d6fb90b', 'all'),
    ('component-A', '/tmp/direct-hmmer-operation-ports-A-20261022-001-btxj3p5g', 'MANIFEST_FINAL001.json', '5dd04a0f1549fee487f15b072b12ee82ce479b711791f4f4827c930a36c163a9', 'exclude-fixtures'),
    ('component-B', '/tmp/direct-hmmer-timing-b-008-evidence-cfaehck6', 'MANIFEST_FINAL001.json', '5ef8f1071d3ae57f5927b7e0c8588c376d90d1e2050d22f8615dd79214c910e8', 'exclude-fixtures'),
    ('component-C', '/tmp/direct-hmmer-C008-evidence-20261022-UHU41U', 'MANIFEST_FINAL001.json', 'd2f6f5a91d6b0372b5ed12d1198da678308fd076148bd0ddca475f0ee15550f9', 'exclude-fixtures'),
    ('boundary-review', '/tmp/direct-hmmer008-boundary-audit-R-20261022-iADg2M', 'MANIFEST001.json', '56c004eb710a472afb2d5e8c801f25418dff85f6565bd43087e631d5edc7318a', 'all'),
    ('worker-preflight', '/tmp/direct-hmmer-worker-preflight-R-20261022-ld5hSb', 'MANIFEST001.json', None, 'all'),
    ('fixture-diagnosis', '/tmp/direct-hmmer-root-resume-diagnosis-R-20261022-wFh8Pj', 'MANIFEST001.json', '4fd6487924dedf743c57d296502e8aa8c545db9c15846bd3b683f79c04617494', 'all'),
    ('root004-independent-review', '/tmp/direct-hmmer-root004-independent-review-20261022-001-4mcjxgzj', 'MANIFEST_FINAL001.json', 'b2fd535d0b5f4ee69893fdf798defd3859ea07b26b7eb8de0dce21bcd89781b2', 'all'),
    ('resource-prefix', '/tmp/configured-resource-prefix-R-20261022-zWmbii', 'MANIFEST001.json', '8a39d866bd104c4c7fbcd2bfb9781df079fca20028d4f6509b6459411914391c', 'all'),
    ('resource-choice8', '/tmp/configured-resource-root-choice8-R-20261022-aIDjVo', 'MANIFEST001.json', 'd34b6e8147547e506a5e0fa4ab383f63dce5e25334b1699f9567b7d9f0d32b5b', 'all'),
    ('resource-choice-offline-review', '/tmp/configured-resource-choice-root-review-20261022-001', 'MANIFEST001.json', 'dafc931b709090643442c85fcc2f75a6b95d89476ac307dd3d032d61283be1cd', 'all'),
    ('literature-return-boundary002', '/tmp/configured-literature-return-boundary-root-20261022-002', 'MANIFEST001.json', '95cc6779f0b683986972a9aba457253cf7f9fb143ff44ceed3e366c05c229556', 'all'),
    ('next-caller-plan', '/tmp/configured-direct-timing-caller-plan-R-20261022-hRKfbD', 'MANIFEST001.json', '9d99df7d2f98bc6dcfd79ea4548f81abbbf88219c95202a1c102f4c635f3f632', 'all'),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def facts(item):
    return {'device': item.st_dev, 'inode': item.st_ino, 'bytes': item.st_size,
            'mode': stat.S_IMODE(item.st_mode), 'mtime_ns': item.st_mtime_ns,
            'ctime_ns': item.st_ctime_ns, 'nlink': item.st_nlink}


def read(path):
    # No alias resolution is permitted, including ancestors in selected paths.
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise RuntimeError('alias_in_selected_source:' + str(ancestor))
    initial = path.lstat()
    assert stat.S_ISREG(initial.st_mode), path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        assert facts(os.fstat(fd)) == facts(initial), path
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read()
        assert facts(os.fstat(fd)) == facts(initial), path
    finally:
        os.close(fd)
    assert facts(path.lstat()) == facts(initial) and len(data) == initial.st_size, path
    return data, {**facts(initial), 'sha256': sha(data)}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def rows(value):
    candidates = [value.get(key) for key in ('members', 'files', 'regular_members')]
    for member_rows in candidates:
        if isinstance(member_rows, dict):
            return [{'path': key, **item} for key, item in member_rows.items()]
        if isinstance(member_rows, list):
            return [dict(item, path=item.get('path', item.get('relative_path'))) for item in member_rows]
    raise RuntimeError('unsupported_manifest_member_shape')


def alias(path):
    initial = path.lstat()
    assert stat.S_ISLNK(initial.st_mode), path
    literal = os.readlink(path)
    assert facts(path.lstat()) == facts(initial) and os.readlink(path) == literal, path
    return {'source_path': str(path), 'literal_target': literal,
            'literal_target_utf8_sha256': sha(literal.encode()),
            'before': facts(initial), 'after': facts(initial),
            'followed': False, 'copied': False}


def prior_guard():
    old, witness = read(OLD)
    assert sha(old) == OLD_SHA
    raw, manifest_witness = read(PRIOR / 'MANIFEST.json')
    assert sha(raw) == PRIOR_MANIFEST_SHA
    manifest = json.loads(raw)
    saved = {}
    for name, item in manifest['members'].items():
        data, observed = read(PRIOR / name)
        assert sha(data) == item['sha256'] and len(data) == item['bytes']
        assert observed['mode'] == 0o444
        saved[name] = observed
    actual = {str(path.relative_to(PRIOR)) for path in PRIOR.rglob('*') if path.is_file()}
    assert actual == set(saved) | {'MANIFEST.json'}
    assert all(not path.is_symlink() for path in PRIOR.rglob('*'))
    return {'document': witness, 'manifest': manifest_witness, 'members': saved,
            'member_count_excluding_manifest': len(saved)}


def main():
    assert not (HERE / 'candidate001').exists()
    prior_before = prior_guard()
    selected = {}
    coverages = []
    aliases = []

    def select(path, destination, expected=None):
        assert not Path(destination).is_absolute() and '..' not in Path(destination).parts
        assert destination not in selected, destination
        data, witness = read(path)
        if expected is not None:
            assert witness['sha256'] == expected['sha256'], path
            assert len(data) == expected.get('bytes', expected.get('size')), path
        selected[destination] = {'source_path': str(path), 'before': witness,
                                 'target_mode': 0o444 | (witness['mode'] & 0o111),
                                 'bytes': len(data), 'sha256': sha(data)}

    for prefix, directory, name, expected_sha, policy in BUNDLES:
        directory = Path(directory)
        raw, manifest_witness = read(directory / name)
        if expected_sha:
            assert sha(raw) == expected_sha, directory
        value = json.loads(raw)
        members = rows(value)
        regulars = [item for item in members if item.get('node_type', 'file') == 'file']
        saved_aliases = list(value.get('aliases', []))
        saved_aliases += [item for item in members if item.get('node_type') == 'symlink']
        chosen, omitted = [], []
        for item in regulars:
            member = item['path']
            assert member and not Path(member).is_absolute() and '..' not in Path(member).parts
            if policy == 'exclude-fixtures' and FIXTURE_PARTS.intersection(Path(member).parts):
                omitted.append(item)
                continue
            select(directory / member, prefix + '/' + member, item)
            chosen.append(member)
        for item in saved_aliases:
            aliases.append({'bundle': prefix, 'original_manifest_record': item,
                            **alias(directory / item['path'])})
        select(directory / name, prefix + '/' + name)
        coverages.append({'bundle': prefix, 'source_directory': str(directory),
                          'manifest_path': name, 'manifest_sha256': sha(raw),
                          'selection_policy': policy, 'regular_manifest_members': len(regulars),
                          'selected_regular_paths_excluding_manifest': chosen,
                          'omitted_regular_members': omitted,
                          'omission_reason': 'Raw invocation fixture files omitted; source manifests retain original byte/hash/mode records. No fixture replay completeness claimed.',
                          'literal_alias_count': len(saved_aliases), 'alias_targets_followed': 0})

    root = Path('/tmp/direct-hmmer-root008-evidence-20261022-001')
    root_omitted = []
    for base, dirs, files in os.walk(root, followlinks=False):
        base = Path(base)
        for child in list(dirs):
            path = base / child
            if path.is_symlink():
                aliases.append({'bundle': 'root-engineering', **alias(path)})
                dirs.remove(child)
        for child in files:
            path = base / child
            member = str(path.relative_to(root))
            if path.is_symlink():
                aliases.append({'bundle': 'root-engineering', **alias(path)})
            elif FIXTURE_PARTS.intersection(Path(member).parts):
                root_omitted.append({'path': member, 'bytes': path.lstat().st_size,
                                     'mode': stat.S_IMODE(path.lstat().st_mode),
                                     'hash_recomputed': False,
                                     'original_inventory': member.split('/')[0] + '/ORIGINAL_PRESERVATION.json'})
            else:
                select(path, 'root-engineering/' + member)
    coverages.append({'bundle': 'root-engineering', 'source_directory': str(root),
                      'source_status': 'unsealed_root_evidence_exact_selected_regular_guards',
                      'omitted_regular_members': root_omitted,
                      'omission_reason': 'All raw fixture trees omitted; original preservation manifests retained. Only literal alias paths/targets inspected; no raw fixture file bytes opened.',
                      'literal_alias_count': sum(item['bundle'] == 'root-engineering' for item in aliases)})

    static_review = Path('/tmp/direct-hmmer008-snapshot-root-review-20261022-001')
    for name in ('verify.py', 'RESULT001.json'):
        select(static_review / name, 'static-source-root-review/' + name)
    coverages.append({'bundle': 'static-source-root-review', 'source_directory': str(static_review),
                      'source_status': 'explicit_unsealed_root_review_two_regular_members',
                      'selected_regular_paths': ['verify.py', 'RESULT001.json'],
                      'scope': 'Saved independent static preservation result only; no reexecution.'})
    handoff = Path('/tmp/configured-direct-timing-preparation-handoff-root-20261022-001')
    for name in ('HANDOFF001.json', 'OPERATOR_OUTPUT_SCHEMA001.json'):
        select(handoff / name, 'next-caller-handoff/' + name)
    coverages.append({'bundle': 'next-caller-handoff', 'source_directory': str(handoff),
                      'source_status': 'unsealed_root_handoff_two_exact_regular_members',
                      'selected_regular_paths': ['HANDOFF001.json', 'OPERATOR_OUTPUT_SCHEMA001.json'],
                      'scope': 'Adopted static preparation author/checker interface; no actual execution.'})
    select(OLD, 'lineage/PROGRESS018.md')
    select(PRIOR / 'MANIFEST.json', 'lineage/MANIFEST018.json')
    select(REPO / 'docs/DIRECT_HMMER_TIMING_SCOPE_2026-10-22_001.md', 'scopes/DIRECT_HMMER_TIMING_SCOPE_2026-10-22_001.md')
    select(REPO / 'docs/CONFIGURED_DIRECT_TIMING_CALLER_ACTUAL_SCOPE_2026-10-22_001.md',
           'scopes/CONFIGURED_DIRECT_TIMING_CALLER_ACTUAL_SCOPE_2026-10-22_001.md')
    for name in ('prepare019.py', 'publish019.py', 'NEW_EVIDENCE001.md',
                 'AUTHORING_SCOPE001.md', 'AUTHORING_FIRST_FAILURE001.json'):
        select(HERE / name, 'publication/' + name)
    fixed = (HERE / 'RETAINED_CHECKLIST001.md').read_bytes()
    previous = OLD.read_text()
    expected_fixed = previous[previous.index('## Retained correction checklist'):previous.index('## Actual resource preparation, independent verification and launch')].encode()
    assert fixed == expected_fixed and len(re.findall(rb'^- \[[ x]\] \*\*', fixed, re.M)) == 41
    body = ('# Separate permanent progress record019 — unadopted draft\n\n'
            'This draft follows unchanged018, SHA256 ' + OLD_SHA + '. Its same41 IDs, order, checked states and historical descriptions follow verbatim. Selected new evidence follows. No whole-goal item is closed. This candidate is not yet adopted or published.\n\n').encode() + fixed + (HERE / 'NEW_EVIDENCE001.md').read_bytes()
    assert body[body.index(b'## Retained correction checklist'):body.index(b'## Actual resource preparation, independent verification and launch')] == fixed
    write(HERE / 'DRAFT019.md', body)
    pending = {'version': 'progress019_pending_selection_v1', 'status': 'draft_ready_for_root_review_not_published',
               'pending': [],
               'initially_pending': ['Q-root004-independent-review', 'R-next-caller-plan'],
               'received_since_assignment': ['Q-root004-independent-review', 'R-next-caller-plan'],
               'publish_authorized': False, 'goal_status': 'active_incomplete'}
    write(HERE / 'PENDING_SELECTION001.json', encoded(pending))
    selection = {'version': 'progress019_selected_regular_inputs_v1',
                 'status': 'draft_ready_for_root_review_not_published',
                 'members': selected, 'member_count': len(selected),
                 'source_byte_total': sum(item['bytes'] for item in selected.values()),
                 'alias_targets_followed': 0, 'raw_fixture_trees_copied': 0,
                 'coverage': coverages, 'literal_aliases': aliases}
    write(HERE / 'SELECTION001.json', encoded(selection))
    write(HERE / 'LITERAL_ALIASES001.json', encoded({'version': 'literal_alias_inventory_v1',
          'aliases': aliases, 'alias_count': len(aliases), 'followed': 0, 'recreated': 0,
          'scope': 'Literal readlink/lstat only; all aliases omitted from candidate members.'}))
    candidate = HERE / 'candidate001'
    candidate.mkdir()
    for target, item in selected.items():
        data, before = read(Path(item['source_path']))
        assert before == item['before'], target
        write(candidate / target, data)
        (candidate / target).chmod(item['target_mode'])
        assert read(Path(item['source_path']))[1] == before, target
        item['after'] = before
    write(candidate / 'PROGRESS.md', body)
    for name in ('SELECTION001.json', 'LITERAL_ALIASES001.json', 'PENDING_SELECTION001.json'):
        write(candidate / 'publication' / name, (HERE / name).read_bytes())
    write(candidate / 'COPY_CONTROLS001.json', encoded(selected))
    for target, item in selected.items():
        assert read(Path(item['source_path']))[1] == item['before'], target
    for item in aliases:
        current = alias(Path(item['source_path']))
        assert current['before'] == item['before'] and current['literal_target'] == item['literal_target']
    prior_after = prior_guard()
    assert prior_before == prior_after
    write(HERE / 'PRIOR018_GUARDS001.json', encoded({'before': prior_before, 'after': prior_after,
          'equal': True, 'atime_compared': False, 'prior018_not_replaced': True}))
    write(candidate / 'PRIOR018_GUARDS001.json', (HERE / 'PRIOR018_GUARDS001.json').read_bytes())
    for path in (HERE / 'publish019.py', HERE / 'prepare019.py'):
        ast.parse(path.read_bytes(), filename=str(path))
    validation = {'version': 'progress019_draft_static_checks_v1', 'status': 'draft_only_not_published',
                  'fixed41_exact': True, 'fixed41_count': 41, 'fixed_chunk_sha256': sha(fixed),
                  'fixed_chunk_bytes': len(fixed), 'prior018_unchanged': True,
                  'selected_source_guards_equal': True, 'alias_targets_followed': 0,
                  'omitted_raw_A_B_C_root_fixture_bodies_read': 0,
                  'closed_Q_review_bundle_files_hashed_and_copied': True,
                  'publisher_executed': False,
                  'application_database_test_model_network_native_control_calls': 0,
                  'draft_sha256': sha(body), 'pending_selection_count': len(pending['pending']),
                  'ast_parse': 'passed'}
    write(HERE / 'DRAFT_STATIC_CHECKS001.json', encoded(validation))
    write(candidate / 'DRAFT_STATIC_CHECKS001.json', encoded(validation))
    all_members = {}
    for path in sorted(candidate.rglob('*')):
        if path.is_file():
            relative = str(path.relative_to(candidate))
            path.chmod(selected.get(relative, {}).get('target_mode', 0o444))
            data, witness = read(path)
            all_members[relative] = {'sha256': sha(data), 'bytes': len(data), 'mode': format(witness['mode'], '04o')}
    manifest = {'version': 'progress019_unadopted_candidate_manifest_v1',
                'status': 'draft_ready_for_root_review_not_published',
                'members': all_members, 'member_count': len(all_members),
                'member_bytes': sum(item['bytes'] for item in all_members.values()),
                'report_sha256': sha(body), 'fixed41_verbatim': True,
                'prior018_sha256': OLD_SHA, 'prior018_manifest_sha256': PRIOR_MANIFEST_SHA,
                'pending_selection_ids': [item['id'] for item in pending['pending']],
                'goal_status': 'active_incomplete', 'actual_publication_performed': False}
    write(candidate / 'MANIFEST.json', encoded(manifest))
    (candidate / 'MANIFEST.json').chmod(0o444)
    for directory in sorted((p for p in candidate.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        directory.chmod(0o555)
    candidate.chmod(0o555)
    print(json.dumps({'draft': str(HERE / 'DRAFT019.md'), 'draft_sha256': sha(body),
          'candidate': str(candidate), 'manifest_sha256': sha((candidate / 'MANIFEST.json').read_bytes()),
          'selected_regular_sources': len(selected), 'candidate_members_excluding_manifest': len(all_members),
          'literal_aliases_not_followed': len(aliases), 'pending_selection_count': len(pending['pending']),
          'permanent_writes': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
