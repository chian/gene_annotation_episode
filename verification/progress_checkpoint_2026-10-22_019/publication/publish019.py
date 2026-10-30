"""Future no-replace publication of an explicitly reviewed progress019 candidate.

Authored only for this workload. Current pending draft cannot pass preflight.
No application imports, SQLite access, tests or investigation work occurs here.
"""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import re
import stat
import tempfile

REPO = Path('/home/chia/repos/gene_annotation_episode')
OLD = REPO / 'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_018.md'
DOC = REPO / 'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_019.md'
OUT = REPO / 'verification/progress_checkpoint_2026-10-22_019'
PRIOR = REPO / 'verification/progress_checkpoint_2026-10-22_018'
OLD_SHA = 'fb3845dfda7a6852ec755afc0cf8df6b859c0941c517fab72b57c9248a7f4834'
PRIOR_MANIFEST_SHA = '4925b94b70693753e9ad0364aee43c5cc74dc51a2632aaebaac915ac011cf488'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def fields(item):
    return {'device': item.st_dev, 'inode': item.st_ino, 'bytes': item.st_size,
            'mode': stat.S_IMODE(item.st_mode), 'mtime_ns': item.st_mtime_ns,
            'ctime_ns': item.st_ctime_ns, 'nlink': item.st_nlink}


def read(path):
    for item in (path, *path.parents):
        assert not item.is_symlink(), ('selected_alias', str(item))
    initial = path.lstat()
    assert stat.S_ISREG(initial.st_mode), path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        assert fields(os.fstat(fd)) == fields(initial), path
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read()
        assert fields(os.fstat(fd)) == fields(initial), path
    finally:
        os.close(fd)
    assert fields(path.lstat()) == fields(initial) and len(data) == initial.st_size, path
    return data, {**fields(initial), 'sha256': sha(data)}


def sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write(path, data, mode=0o444):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(data)
            stream.flush()
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def prior_guard():
    old, observed = read(OLD)
    assert sha(old) == OLD_SHA
    raw, manifest_observed = read(PRIOR / 'MANIFEST.json')
    assert sha(raw) == PRIOR_MANIFEST_SHA
    saved = json.loads(raw)['members']
    checked = {}
    for name, value in saved.items():
        data, witness = read(PRIOR / name)
        assert sha(data) == value['sha256'] and len(data) == value['bytes']
        assert witness['mode'] == 0o444
        checked[name] = witness
    assert {str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()} == set(saved) | {'MANIFEST.json'}
    assert all(not p.is_symlink() for p in PRIOR.rglob('*'))
    return {'document': observed, 'manifest': manifest_observed, 'members': checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-contract', type=Path, required=True)
    parser.add_argument('--reviewed-contract-sha256', required=True)
    args = parser.parse_args()
    raw, contract_stat = read(args.reviewed_contract)
    assert sha(raw) == args.reviewed_contract_sha256
    contract = json.loads(raw)
    required = {'version', 'status', 'candidate_directory', 'candidate_manifest_sha256',
                'report_sha256', 'selection_sha256', 'prior018_sha256',
                'prior018_manifest_sha256', 'fixed_chunk_sha256',
                'pending_selection_ids', 'goal_status', 'report_path', 'capsule_path'}
    assert set(contract) == required
    assert contract['version'] == 'progress019_reviewed_publication_contract_v1'
    assert contract['status'] == 'reviewed_ready_to_publish'
    assert contract['pending_selection_ids'] == [] and contract['goal_status'] == 'active_incomplete'
    assert contract['report_path'] == str(DOC) and contract['capsule_path'] == str(OUT)
    assert contract['prior018_sha256'] == OLD_SHA
    assert contract['prior018_manifest_sha256'] == PRIOR_MANIFEST_SHA
    assert not os.path.lexists(DOC) and not os.path.lexists(OUT)
    candidate = Path(contract['candidate_directory'])
    candidate_raw, _ = read(candidate / 'MANIFEST.json')
    assert sha(candidate_raw) == contract['candidate_manifest_sha256']
    manifest = json.loads(candidate_raw)
    assert manifest['status'] == 'reviewed_ready_to_publish'
    assert manifest['pending_selection_ids'] == []
    members = manifest['members']
    actual = set()
    for base, directories, files in os.walk(candidate, followlinks=False):
        base = Path(base)
        assert all(not (base / name).is_symlink() for name in directories)
        for name in files:
            path = base / name
            assert not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode)
            actual.add(str(path.relative_to(candidate)))
    assert actual == set(members) | {'MANIFEST.json'}
    selection_raw, _ = read(candidate / 'publication/SELECTION001.json')
    assert sha(selection_raw) == contract['selection_sha256']
    selection = json.loads(selection_raw)
    assert selection['status'] == 'reviewed_ready_to_publish'
    assert selection['alias_targets_followed'] == 0
    selected = selection['members']
    prior_before = prior_guard()
    old = read(OLD)[0]
    fixed = old[old.index(b'## Retained correction checklist'):old.index(b'## Actual resource preparation, independent verification and launch')]
    assert len(re.findall(rb'^- \[[ x]\] \*\*', fixed, re.M)) == 41
    assert sha(fixed) == contract['fixed_chunk_sha256']
    body, _ = read(candidate / 'PROGRESS.md')
    assert sha(body) == contract['report_sha256']
    assert body[body.index(b'## Retained correction checklist'):body.index(b'## Actual resource preparation, independent verification and launch')] == fixed
    # Verify every selected original regular input, retaining source modes/stat.
    for target, item in selected.items():
        assert not Path(target).is_absolute() and '..' not in Path(target).parts
        _, witness = read(Path(item['source_path']))
        assert witness == item['before'], target
    for item in selection['literal_aliases']:
        path = Path(item['source_path'])
        assert stat.S_ISLNK(path.lstat().st_mode)
        assert fields(path.lstat()) == item['before']
        assert os.readlink(path) == item['literal_target']
    stage = Path(tempfile.mkdtemp(prefix='.' + OUT.name + '-staging-', dir=OUT.parent))
    publication_phase = 'retained_unpublished_stage'
    try:
        copied = {}
        for name, item in members.items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            data, witness = read(candidate / name)
            mode = int(item['mode'], 8) if isinstance(item['mode'], str) else item['mode']
            assert mode in {0o444, 0o555} and witness['mode'] == mode
            assert sha(data) == item['sha256'] and len(data) == item['bytes']
            write(stage / name, data, mode)
            assert read(candidate / name)[1] == witness
            copied[name] = {'before': witness, 'after': witness, 'source': str(candidate / name)}
        extras = {
            'publication/REVIEWED_CANDIDATE_MANIFEST.json': candidate_raw,
            'publication/REVIEWED_CONTRACT.json': raw,
            'PUBLICATION_COPY_CONTROLS.json': encoded(copied),
        }
        for name, data in extras.items():
            assert name not in members
            write(stage / name, data)
        for target, item in selected.items():
            assert read(Path(item['source_path']))[1] == item['before'], target
        assert prior_guard() == prior_before
        assert read(args.reviewed_contract)[1] == contract_stat
        final_members = {}
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                data, witness = read(path)
                final_members[str(path.relative_to(stage))] = {
                    'sha256': sha(data), 'bytes': len(data), 'mode': format(witness['mode'], '04o')}
        final_manifest = {'version': 'permanent_progress_checkpoint_v1',
                          'status': 'published_additive_progress_record', 'members': final_members,
                          'report_sha256': sha(body), 'report_path': str(DOC),
                          'fixed41_verbatim': True, 'goal_status': 'active_incomplete',
                          'prior018_sha256': OLD_SHA, 'pending_selection_ids': [],
                          'aliases_copied_or_followed': 0}
        write(stage / 'MANIFEST.json', encoded(final_manifest))
        for directory in sorted((p for p in stage.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            directory.chmod(0o555)
            sync(directory)
        stage.chmod(0o555)
        sync(stage)
        libc = ctypes.CDLL(None, use_errno=True)
        rename = libc.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        assert rename(-100, os.fsencode(stage), -100, os.fsencode(OUT), 1) == 0, ctypes.get_errno()
        publication_phase = 'capsule_published_report_link_pending'
        sync(OUT.parent)
        os.link(OUT / 'PROGRESS.md', DOC, follow_symlinks=False)
        publication_phase = 'report_linked_durability_pending'
        sync(DOC.parent)
        assert read(OLD)[0] == old
        assert read(DOC)[0] == body and read(OUT / 'PROGRESS.md')[0] == body
        for name, item in final_members.items():
            data, witness = read(OUT / name)
            assert sha(data) == item['sha256'] and len(data) == item['bytes']
            assert witness['mode'] == int(item['mode'], 8)
        print(json.dumps({'status': 'published_additive_progress_record', 'report': str(DOC),
                          'report_sha256': sha(body), 'capsule': str(OUT),
                          'manifest_sha256': sha(read(OUT / 'MANIFEST.json')[0]),
                          'members_excluding_manifest': len(final_members),
                          'fixed41_verbatim': True, 'goal_status': 'active_incomplete'}, sort_keys=True))
    except BaseException:
        # Never remove/replace a partial stage or already published path.
        print(json.dumps({'status': 'failed_partial_preserved', 'phase': publication_phase,
                          'stage_path': str(stage), 'capsule_path': str(OUT),
                          'report_path': str(DOC), 'cleanup_or_retry': False}), flush=True)
        raise


if __name__ == '__main__':
    main()
