#!/usr/bin/env python3
"""Assemble reviewed, final input handoffs without publishing a capsule (002).

No application import, SQLite open, subprocess, test or provider call occurs.
This operator runs only after root finalizes a ready=true handoff declaration.
It can create NEW sealed copies of completed root engineering evidence whose
original directories do not already have owner manifests. It never writes an
original tree. Existing W1/R/Q owner bundles are consumed in place exactly once.
Only the one explicitly bound original ROOT FIFO may be recorded by lstat
metadata. It is never opened and its stream is never represented as copied.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

import build_publication as common


HERE = Path(__file__).absolute().parent
CHECKOUT = Path('/tmp/gene-annotation-configured-caller-20261022-007')
NEW_SOURCE_INPUTS = {
    'gene_annotation_episode/local_commission_frame.py',
    'tests/test_local_commission_frame.py',
    'tests/test_local_return_evidence.py',
    'tests/test_local_commission_frame_runtime.py',
    'tests/test_local_commission_frame_reconstruction.py',
    'scripts/prove_local_commission_frame_reconstruction.py',
    'GENERATION_BASELINE_007.json',
    'GENERATION_TEST_AMENDMENT_007_001.json',
    'docs/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_001.md',
    'docs/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_002.md'}
ROOT_UNSEALED_ALLOWLIST = {
    '/tmp/factual-frame007-root-checks-20261022-o2gix27z',
    '/tmp/factual-frame007-root-checks-20261022-rv2ohe2d'}
FIFO_ROOT = '/tmp/factual-frame007-root-checks-20261022-o2gix27z'
FIFO_RELATIVE = 'pytest-fixtures/test_subprocess_reconstructs_o0/turns.jsonl.gate'
FIFO_METADATA = {
    'source_path': FIFO_ROOT + '/' + FIFO_RELATIVE,
    'type': 'fifo', 'mode': '0664', 'mtime_ns': 1792666730569956344,
    'inode': 191105287, 'device': 2050, 'size': 0}
FIFO_REPRESENTATION = FIFO_RELATIVE + '.FIFO_METADATA_ONLY.json'


def original_root_snapshot(root, *, fifo_nodes):
    """Read regular files; only nofollow-stat the exact declared fixture FIFO.

    This source-only snapshot has an extra fifo_nodes category. The unchanged
    general builder/checker snapshot still rejects every special filesystem
    node. No FIFO is constructed in a sealed copy or the permanent capsule.
    """
    root = common.absolute(str(root))
    expected = {FIFO_RELATIVE: FIFO_METADATA} if str(root) == FIFO_ROOT else {}
    common.require(common.plain_json(fifo_nodes) == common.plain_json(expected),
                   'FIFO metadata operand differs from exact permitted ROOT fixture')
    initial = root.lstat()
    common.require(stat.S_ISDIR(initial.st_mode), 'original root is not a real directory')
    result = {'root': common.metadata(initial), 'directories': {}, 'files': {},
              'aliases': {}, 'fifo_nodes': {}}
    def visit(directory):
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            path = Path(entry.path)
            name = path.relative_to(root).as_posix()
            common.relative(name)
            info = entry.stat(follow_symlinks=False)
            if name in expected:
                common.require(stat.S_ISFIFO(info.st_mode),
                               'declared fixture FIFO changed type; no stream opened')
                metadata = {'source_path': str(path), 'type': 'fifo',
                            **common.metadata(info), 'size': info.st_size}
                common.require(metadata == expected[name],
                               'declared FIFO identity changed; no stream opened: ' + str(path))
                result['fifo_nodes'][name] = metadata
            elif stat.S_ISLNK(info.st_mode):
                result['aliases'][name] = {'target': os.readlink(path), **common.metadata(info)}
            elif stat.S_ISDIR(info.st_mode):
                result['directories'][name] = common.metadata(info)
                visit(path)
                common.require(common.metadata(path.lstat()) == common.metadata(info),
                               'original directory changed during source scan')
            elif stat.S_ISREG(info.st_mode):
                result['files'][name] = common.read_regular(path)[1]
            elif stat.S_ISFIFO(info.st_mode):
                raise ValueError('undeclared FIFO rejected without opening it: ' + str(path))
            else:
                raise ValueError('undeclared special source node rejected without opening it: ' + str(path))
    visit(root)
    common.require(result['fifo_nodes'] == expected, 'declared original FIFO missing or changed')
    common.require(common.metadata(root.lstat()) == result['root'], 'original root changed during scan')
    return result


def descriptor(path):
    path = common.absolute(str(path))
    _, witness = common.read_regular(path)
    return {'path': str(path), 'sha256': witness['sha256'], 'bytes': witness['bytes']}


def write_unique(path, data, *, readonly=False):
    path = common.absolute(str(path))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(data)
            stream.flush()
        if readonly:
            os.fchmod(fd, 0o444)
        os.fsync(fd)
    finally:
        os.close(fd)
    common.fsync_directory(path.parent)


def seal_root_handoff(specification):
    source = common.absolute(specification['path'])
    common.require(str(source) in ROOT_UNSEALED_ALLOWLIST,
                   'only the two named completed root invocations may be sealed here')
    common.require(specification['final'] is True and specification['synthetic_engineering_only'] is True,
                   'root handoff has not been declared final synthetic engineering evidence')
    final = common.absolute(specification['sealed_copy'])
    common.require(not os.path.lexists(final), 'sealed-copy target already exists')
    required = specification['required_final_files']
    common.require({'RESULTS.json', 'INPUTS_BEFORE.json', 'INPUTS_AFTER.json', 'COMMAND.json',
                    'junit.xml', 'stdout.log', 'stderr.log'} <= set(required),
                   'root handoff lacks a final result/guard/XML/log/command selection')
    for relative, expectation in required.items():
        common.relative(relative)
        common.checked_descriptor({'path': str(source/relative), **expectation})
    fifo_nodes = specification['fifo_nodes']
    before = original_root_snapshot(source, fifo_nodes=fifo_nodes)
    stage = Path(tempfile.mkdtemp(prefix='.' + final.name + '-staging-', dir=final.parent))
    files, aliases, kinds, fifo_representations = {}, {}, {}, {}
    for relative in before['directories']:
        (stage/relative).mkdir(parents=True, exist_ok=True)
    for relative, witness in before['files'].items():
        data, actual = common.read_regular(source/relative)
        common.require(actual == witness, 'root source changed before copy')
        target = stage/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        write_unique(target, data, readonly=True)
        os.utime(target, ns=(actual['mtime_ns'], actual['mtime_ns']), follow_symlinks=False)
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        files[relative] = {'source': str(source/relative), 'before': actual,
                           'copy_equals_source': True}
        kinds[relative] = 'original_completed_root_engineering_evidence'
    for relative, metadata in before['fifo_nodes'].items():
        common.require(relative == FIFO_RELATIVE, 'unexpected FIFO representation request')
        member = FIFO_REPRESENTATION
        common.require(all(member not in before[group] for group in
                           ('files', 'directories', 'aliases', 'fifo_nodes')),
                       'FIFO metadata record would collide with original membership')
        record = {'version': 'fixture_fifo_metadata_only_v1', **metadata}
        encoded = common.plain_json(record)
        write_unique(stage/member, encoded, readonly=True)
        kinds[member] = 'generated_fifo_metadata_only_not_copied_stream'
        fifo_representations[relative] = {
            'source_relative': relative, 'representation_member': member,
            'representation_sha256': common.digest(encoded), 'metadata': metadata,
            'byte_copy_claimed': False, 'stream_opened': False}
    for relative, row in before['aliases'].items():
        original_target = row['target']
        lexical_target = Path(os.path.normpath(os.path.join(str((source/relative).parent), original_target)))
        common.require(lexical_target.is_relative_to(source), 'root alias points outside the captured root')
        target_member = lexical_target.relative_to(source).as_posix()
        common.require(target_member in before['files'] or target_member in before['directories'],
                       'root alias has no positive retained target')
        rebased = os.path.relpath(target_member, os.path.dirname(relative))
        (stage/relative).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(rebased, stage/relative)
        aliases[relative] = {'original_path': str(source/relative), 'original_target': original_target,
                            'published_target': rebased, 'target_member': target_member}
    for relative, row in files.items():
        row['after'] = common.read_regular(row['source'])[1]
        common.require(row['before'] == row['after'], 'root original changed after copying')
    after = original_root_snapshot(source, fifo_nodes=fifo_nodes)
    common.require(before == after, 'root original membership or metadata changed during copy')
    controls = {'version': 'completed_root007_evidence_copy_controls_v2', 'source_root': str(source),
                'source_before': before, 'source_after': after, 'files': files, 'aliases': aliases,
                'fifo_representations': fifo_representations,
                'originals_unchanged': True, 'original_data_opened_as_databases': False,
                'fifo_streams_opened_read_or_written': False}
    write_unique(stage/'ORIGINAL_COPY_CONTROLS.json', common.plain_json(controls), readonly=True)
    kinds['ORIGINAL_COPY_CONTROLS.json'] = 'exact_before_after_original_copy_controls'
    write_unique(stage/'SEALING_INPUTS.json', common.plain_json(specification), readonly=True)
    kinds['SEALING_INPUTS.json'] = 'root_finalized_handoff_declaration'
    captured = common.snapshot(stage)
    rows = [{'path': name, 'kind': kinds[name], 'sha256': witness['sha256'],
             'bytes': witness['bytes'], 'mode': '0444'}
            for name, witness in sorted(captured['files'].items())]
    manifest = {'version': 'completed_root007_engineering_evidence_manifest_v1',
        'regular_members': rows, 'aliases': aliases,
        'listed_regular_member_count': len(rows), 'listed_regular_bytes': sum(row['bytes'] for row in rows),
        'physical_regular_member_count_including_manifest': len(rows) + 1,
        'directory_count_including_root': len(captured['directories']) + 1,
        'regular_mode': '0444', 'directory_mode': '0555', 'manifest_self_excluded': True,
        'source_originals_unchanged': True}
    write_unique(stage/'MANIFEST.json', common.plain_json(manifest), readonly=True)
    for name in sorted(captured['directories'], key=lambda value: (-value.count('/'), value)):
        os.chmod(stage/name, 0o555)
        common.fsync_directory(stage/name)
    os.chmod(stage, 0o555)
    common.fsync_directory(stage)
    common.rename_noreplace(stage, final)
    common.fsync_directory(final.parent)
    common.require(original_root_snapshot(source, fifo_nodes=fifo_nodes) == before,
                   'root original changed at sealing completion')
    return {'path': str(final), 'manifest': descriptor(final/'MANIFEST.json'),
            'final': True, 'synthetic_engineering_only': True}


def prepare(configuration):
    common.require(configuration.get('version') == 'factual_frame007_final_handoffs_v1'
                   and configuration.get('ready') is True,
                   'final handoffs are not ready; no evidence copies or input files may be created')
    common.require(configuration['checkout'] == str(CHECKOUT), 'wrong generation007 checkout')
    baseline_path = CHECKOUT/'GENERATION_BASELINE_007.json'
    baseline_raw, _ = common.checked_descriptor({'path': str(baseline_path), 'sha256': common.BASELINE_SHA})
    baseline = json.loads(baseline_raw)
    source_inventory = {}
    for relative in sorted(set(baseline['files']) | NEW_SOURCE_INPUTS):
        row = descriptor(CHECKOUT/relative)
        if relative.startswith(('gene_annotation_episode/', 'method_loop/')) and relative.endswith('.py'):
            kind = 'application_implementation'
        elif relative.startswith('tests/'):
            kind = 'current_test_source'
        elif relative.startswith('scripts/'):
            kind = 'synthetic_operator_source'
        elif relative.startswith('docs/'):
            kind = 'normative_or_adopted_scope'
        else:
            kind = 'baseline_static_or_configuration_input'
        source_inventory[relative] = {'source': row['path'], 'sha256': row['sha256'],
                                      'bytes': row['bytes'], 'kind': kind}
    common.require(common.runtime_identity(source_inventory) == (137, configuration['runtime_pin']),
                   'final source pin changed or differs from root handoff')
    amendment_raw, _ = common.checked_descriptor(configuration['test_amendment_authority'])
    amendment = json.loads(amendment_raw)
    common.require(amendment['scope']['sha256'] == common.AMENDMENT_SCOPE_SHA
                   and set(amendment['files']) == common.TEST_AMENDMENTS,
                   'wrong two-test amendment authority')
    authority_directory = common.absolute(configuration['generated_patch_directory'])
    authority_directory.mkdir(mode=0o700)
    amendments, external = [], list(configuration['external_refs'])
    for name, row in sorted(amendment['files'].items()):
        original = common.absolute(row['original']['preserved'])
        old, old_witness = common.read_regular(original)
        new, new_witness = common.read_regular(CHECKOUT/name)
        common.require(old_witness['sha256'] == row['original']['sha256'] == baseline['files'][name]['sha256']
                       and new_witness['sha256'] == row['amended']['sha256'] == source_inventory[name]['sha256'],
                       'test amendment endpoint bytes changed')
        patch = ''.join(difflib.unified_diff(old.decode('utf-8').splitlines(keepends=True),
            new.decode('utf-8').splitlines(keepends=True), fromfile='a/' + name,
            tofile='b/' + name)).encode('utf-8')
        patch_path = authority_directory/(Path(name).name + '.patch')
        write_unique(patch_path, patch, readonly=True)
        original_member = 'authority/amendments/' + Path(name).name + '.original'
        patch_member = 'authority/amendments/' + patch_path.name
        external.extend([
            {**descriptor(original), 'copy_member': original_member, 'extent': 'exact original test bytes',
             'meaning': 'Scope002 preserved original endpoint; no old test is silently ignored.'},
            {**descriptor(patch_path), 'copy_member': patch_member, 'extent': 'single-file unified test patch',
             'meaning': 'Purely verifiable original-to-final scope002 assertion amendment.'}])
        amendments.append({'path': name, 'baseline_sha256': old_witness['sha256'],
            'final_sha256': new_witness['sha256'],
            'scope_member': 'source/docs/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_002.md',
            'original_member': original_member, 'patch_member': patch_member})
    evidence = {}
    common.require(set(configuration['evidence_handoffs']) >= {'W1', 'R', 'Q', 'Q_SCOPE002', 'ROOT', 'ROOT_SCOPE002'},
                   'required source-qualified evidence handoff omitted')
    for owner, specification in configuration['evidence_handoffs'].items():
        common.require(specification.get('final') is True, 'unfinished owner handoff: ' + owner)
        if 'sealed_copy' in specification:
            evidence[owner] = seal_root_handoff(specification)
        else:
            common.checked_descriptor(specification['manifest'])
            common.require(specification['synthetic_engineering_only'] is True, 'nonengineering evidence root')
            evidence[owner] = specification
    common.require(evidence['Q']['path'] == '/tmp/gene-annotation-Q007-reconstruction-evidence-20261022-001',
                   'original sealed Q bundle path differs')
    common.require(evidence['Q_SCOPE002']['path'] != evidence['Q']['path'], 'Q003 must be a distinct sealed handoff')
    all_sources = set()
    trees = {}
    for owner, specification in evidence.items():
        root = common.absolute(specification['path'])
        trees[owner] = common.snapshot(root)
        common.validate_owner_manifest(specification, trees[owner])
        all_sources.add(str(root))
        all_sources.update(str(root/name) for kind in ('files', 'directories') for name in trees[owner][kind])
    aliases = {}
    for owner, tree in trees.items():
        root = common.absolute(evidence[owner]['path'])
        for name, row in tree['aliases'].items():
            source = str(root/name)
            target = os.path.normpath(os.path.join(str((root/name).parent), row['target']))
            common.require(target in all_sources, 'outside-known-data alias requires root diagnosis: ' + source)
            aliases[source] = {'original_target': row['target'], 'target_source': target, 'authority': None}
    selected = []
    for row in configuration['selected_invocations']:
        owner = row['evidence_name']
        root = common.absolute(evidence[owner]['path'])
        result = {key: row[key] for key in ('id', 'evidence_name', 'expected_counts', 'runtime_pin',
                                          'classification', 'passed_at_final_pin')}
        for field in ('xml', 'log'):
            relative = common.relative(row[field]['relative'])
            result[field] = descriptor(root/relative)
            common.require(result[field]['sha256'] == row[field]['sha256'], 'selected handoff bytes differ')
        counts = common.xml_result(common.read_regular(result['xml']['path'])[0])[0]
        common.require(counts == row['expected_counts'], 'selected XML differs from owner/root declaration')
        selected.append(result)
    inputs = {'version': 'factual_frame007_build_inputs_v1', 'ready': True,
        'checkout': str(CHECKOUT), 'runtime_pin': configuration['runtime_pin'], 'runtime_files': 137, 'test_files': 222,
        'baseline': descriptor(baseline_path),
        'integration_scope': descriptor(CHECKOUT/'docs/LOCAL_COMMISSION_FRAME_INTEGRATION_SCOPE_2026-10-22_001.md'),
        'source_inventory': source_inventory, 'test_amendments': amendments, 'evidence_roots': evidence,
        'selected_invocations': selected, 'external_refs': external, 'alias_mappings': aliases,
        'report_template': descriptor(HERE/'REPORT_TEMPLATE002.md'), 'builder': descriptor(HERE/'build_publication.py'),
        'checker': descriptor(HERE/'check_publication.py'), 'plan': descriptor(HERE/'PLAN002.md')}
    # Interface and this assembly program are retained as explicit tooling originals.
    for path in (HERE/'PUBLICATION_INTERFACE.json', HERE/'prepare_publication_inputs002.py'):
        inputs['external_refs'].append({**descriptor(path), 'copy_member': 'tooling/' + path.name,
            'extent': 'publication preparation source only', 'meaning': 'Reviewed exact preparation contract/operator.'})
    common.baseline_comparison(inputs, baseline)
    return inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = common.absolute(args.output)
    common.require(not os.path.lexists(output), 'input assembly output already exists')
    raw, _ = common.read_regular(common.absolute(args.configuration))
    value = prepare(json.loads(raw))
    value['external_refs'].append({**descriptor(args.configuration),
        'copy_member': 'tooling/FINAL_HANDOFFS002.json', 'extent': 'exact finalized root handoff configuration',
        'meaning': 'Original reviewed inputs to evidence sealing and input assembly; no self-hash cycle.'})
    write_unique(output, common.plain_json(value))
    print(json.dumps({'inputs': str(output), **descriptor(output), 'published': False}, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
