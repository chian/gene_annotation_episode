"""Metadata-only additive candidate002 finalization; never invoke the publisher."""
from pathlib import Path
import ast
import difflib
import json
import os
import re
import stat
from prepare019 import read, write, sha, encoded, prior_guard

HERE = Path(__file__).resolve().parent
OLD = HERE / 'candidate001'
NEW = HERE / 'candidate002'
OLD_MANIFEST_SHA = '2cf2af1c9251c52bda706aaf4f622b0f0e71a07fe566b1f578cae992293c92b2'


def main():
    assert not NEW.exists()
    prior_before = prior_guard()
    manifest_raw, _ = read(OLD / 'MANIFEST.json')
    assert sha(manifest_raw) == OLD_MANIFEST_SHA
    original = json.loads(manifest_raw)
    fixed = (HERE / 'RETAINED_CHECKLIST001.md').read_bytes()
    assert sha(fixed) == '9c09718416e44229b1e51e3ec1653d8d5ac47f9f510298eef2740e22b93afbc9'
    assert len(re.findall(rb'^- \[[ x]\] \*\*', fixed, re.M)) == 41
    body = ('# Separate permanent progress record019\n\n'
            'This additive record follows unchanged018, SHA256 '
            'fb3845dfda7a6852ec755afc0cf8df6b859c0941c517fab72b57c9248a7f4834. '
            'Its same41 IDs, order, checked states and historical descriptions follow verbatim. '
            'Selected finite evidence follows. No whole-goal item is closed.\n\n').encode() + fixed + (HERE / 'NEW_EVIDENCE002.md').read_bytes()
    assert body[body.index(b'## Retained correction checklist'):body.index(b'## Actual resource preparation, independent verification and launch')] == fixed
    assert b'unadopted progress019 draft' not in body and b'eventual selected' not in body
    write(HERE / 'REVIEWED019.md', body)
    changes = ''.join(difflib.unified_diff((HERE / 'DRAFT019.md').read_text().splitlines(True),
                     body.decode().splitlines(True), fromfile='DRAFT019.md', tofile='REVIEWED019.md'))
    write(HERE / 'DRAFT_TO_REVIEWED002.patch', changes.encode())
    selection = json.loads((HERE / 'SELECTION001.json').read_text())
    selected = selection['members']
    for name, item in selected.items():
        assert read(Path(item['source_path']))[1] == item['before'], name
    selection['status'] = 'reviewed_ready_to_publish'
    selection['initial_draft_selection_sha256'] = sha((HERE / 'SELECTION001.json').read_bytes())
    selection['root_review_decision'] = 'publication/ROOT_REVIEW_DECISION001.json'
    additions = [
        ('NEW_EVIDENCE002.md', 'publication/NEW_EVIDENCE002.md'),
        ('ROOT_REVIEW_DECISION001.json', 'publication/ROOT_REVIEW_DECISION001.json'),
        ('finalize_reviewed019.py', 'publication/finalize_reviewed019.py'),
        ('REVIEWED019.md', 'PROGRESS.md'),
        ('DRAFT_TO_REVIEWED002.patch', 'publication/DRAFT_TO_REVIEWED002.patch'),
        ('DRAFT019.md', 'publication/history/DRAFT019.md'),
        ('SELECTION001.json', 'publication/history/SELECTION_DRAFT001.json'),
    ]
    for source, target in additions:
        data, witness = read(HERE / source)
        assert target not in selected
        selected[target] = {'source_path': str(HERE / source), 'before': witness,
                            'target_mode': 0o444, 'bytes': len(data), 'sha256': sha(data)}
    data, witness = read(OLD / 'MANIFEST.json')
    selected['publication/history/CANDIDATE001_MANIFEST.json'] = {
        'source_path': str(OLD / 'MANIFEST.json'), 'before': witness,
        'target_mode': 0o444, 'bytes': len(data), 'sha256': sha(data)}
    selection['member_count'] = len(selected)
    selection['source_byte_total'] = sum(item['bytes'] for item in selected.values())
    write(HERE / 'SELECTION002.json', encoded(selection))
    NEW.mkdir()
    copied_original = {}
    replacement_names = {'PROGRESS.md', 'publication/SELECTION001.json'}
    for name, item in original['members'].items():
        data, before = read(OLD / name)
        assert sha(data) == item['sha256'] and len(data) == item['bytes']
        assert before['mode'] == int(item['mode'], 8)
        copied_original[name] = before
        if name in replacement_names:
            continue
        write(NEW / name, data)
        (NEW / name).chmod(int(item['mode'], 8))
    for _, target in additions:
        item = selected[target]
        data, before = read(Path(item['source_path']))
        assert before == item['before']
        write(NEW / target, data)
        (NEW / target).chmod(0o444)
    write(NEW / 'publication/history/CANDIDATE001_MANIFEST.json', manifest_raw)
    write(NEW / 'publication/SELECTION001.json', (HERE / 'SELECTION002.json').read_bytes())
    final_guards = {}
    for name, item in selected.items():
        after = read(Path(item['source_path']))[1]
        assert after == item['before'], name
        final_guards[name] = {'source': item['source_path'], 'before': item['before'], 'after': after}
    for name, witness in copied_original.items():
        assert read(OLD / name)[1] == witness, name
    assert read(OLD / 'MANIFEST.json')[0] == manifest_raw
    assert prior_guard() == prior_before
    checks = {'version': 'progress019_reviewed_candidate_checks_v1',
              'status': 'reviewed_ready_to_publish', 'published': False,
              'fixed41_verbatim': True, 'fixed41_chunk_sha256': sha(fixed),
              'prior018_unchanged': True, 'candidate001_unchanged': True,
              'original_selected_inputs_unchanged': True,
              'pending_selection_ids': [], 'root_corrections_applied': 2,
              'draft_language_removed_from_report': True,
              'publisher_executed': False,
              'application_database_test_model_network_native_control_calls': 0,
              'report_sha256': sha(body), 'selection_sha256': sha(encoded(selection))}
    ast.parse((HERE / 'publish019.py').read_bytes())
    ast.parse(Path(__file__).read_bytes())
    write(HERE / 'REVIEWED_STATIC_CHECKS002.json', encoded(checks))
    write(NEW / 'REVIEWED_STATIC_CHECKS002.json', encoded(checks))
    write(NEW / 'REVIEWED_SOURCE_GUARDS002.json', encoded(final_guards))
    members = {}
    for path in sorted(NEW.rglob('*')):
        if path.is_file():
            relative = str(path.relative_to(NEW))
            mode = selected.get(relative, {}).get('target_mode', 0o444)
            path.chmod(mode)
            data, facts = read(path)
            members[relative] = {'sha256': sha(data), 'bytes': len(data), 'mode': format(mode, '04o')}
    final_manifest = {**original, 'version': 'progress019_reviewed_candidate_manifest_v1',
                      'status': 'reviewed_ready_to_publish', 'members': members,
                      'member_count': len(members),
                      'member_bytes': sum(item['bytes'] for item in members.values()),
                      'report_sha256': sha(body), 'pending_selection_ids': [],
                      'candidate001_manifest_sha256': OLD_MANIFEST_SHA,
                      'actual_publication_performed': False,
                      'historical_draft_controls_retained': True}
    write(NEW / 'MANIFEST.json', encoded(final_manifest))
    (NEW / 'MANIFEST.json').chmod(0o444)
    for directory in sorted((p for p in NEW.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        directory.chmod(0o555)
    NEW.chmod(0o555)
    contract = {
        'version': 'progress019_reviewed_publication_contract_v1',
        'status': 'reviewed_ready_to_publish', 'candidate_directory': str(NEW),
        'candidate_manifest_sha256': sha((NEW / 'MANIFEST.json').read_bytes()),
        'report_sha256': sha(body), 'selection_sha256': sha(encoded(selection)),
        'prior018_sha256': 'fb3845dfda7a6852ec755afc0cf8df6b859c0941c517fab72b57c9248a7f4834',
        'prior018_manifest_sha256': '4925b94b70693753e9ad0364aee43c5cc74dc51a2632aaebaac915ac011cf488',
        'fixed_chunk_sha256': sha(fixed), 'pending_selection_ids': [],
        'goal_status': 'active_incomplete',
        'report_path': '/home/chia/repos/gene_annotation_episode/docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_019.md',
        'capsule_path': '/home/chia/repos/gene_annotation_episode/verification/progress_checkpoint_2026-10-22_019',
    }
    write(HERE / 'REVIEWED_CONTRACT002.json', encoded(contract))
    print(json.dumps({'candidate': str(NEW), 'manifest_sha256': contract['candidate_manifest_sha256'],
                      'report': str(HERE / 'REVIEWED019.md'), 'report_sha256': sha(body),
                      'selection_sha256': contract['selection_sha256'],
                      'contract': str(HERE / 'REVIEWED_CONTRACT002.json'),
                      'contract_sha256': sha(encoded(contract)),
                      'publisher_sha256': sha((HERE / 'publish019.py').read_bytes()),
                      'members_excluding_manifest': len(members),
                      'selected_regular_sources': len(selected), 'publisher_executed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
