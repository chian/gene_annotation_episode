"""Host stdlib-only selection staging; no native or application execution."""
from pathlib import Path
import hashlib
import json
import shlex
import struct

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
PRIOR = REPO / 'verification/tool_graders_blast_vdb_fixture_acquisition_2026-10-28_658'
RUNNER = REPO / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529'
ATTEMPT = RUNNER / 'check121_vdb_native661'


def pin(path):
    p = Path(path).resolve(strict=True)
    return dict(path=str(p), size_bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def elf(path):
    data = Path(path).read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('selected_elf64_little_endian_required')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    segments = [struct.unpack_from('<IIQQQQQQ', data, header[5] + i * header[9])
                for i in range(header[10])]
    def address_offset(address):
        for kind, flags, offset, virtual, physical, filesz, memsz, align in segments:
            if kind == 1 and virtual <= address < virtual + filesz:
                return offset + address - virtual
        raise ValueError('unmapped_elf_address')
    def string(offset):
        return data[offset:data.index(b'\0', offset)].decode('ascii')
    interpreter, dynamic = None, []
    for kind, flags, offset, virtual, physical, filesz, memsz, align in segments:
        if kind == 3:
            interpreter = string(offset)
        elif kind == 2:
            for index in range(offset, offset + filesz, 16):
                tag, value = struct.unpack_from('<qQ', data, index)
                if tag == 0:
                    break
                dynamic.append((tag, value))
    strings = [value for tag, value in dynamic if tag == 5]
    names = []
    paths = []
    if strings:
        base = address_offset(strings[0])
        names = [string(base + value) for tag, value in dynamic if tag == 1]
        paths = [dict(tag=tag, value=string(base + value))
                 for tag, value in dynamic if tag in (15, 29)]
    return dict(file=pin(path), interpreter=interpreter, needed=names,
                embedded_library_search_paths=paths)


def main():
    proposal = json.loads((PRIOR / 'NATIVE_OBSERVATION_SELECTION_PROPOSAL.json').read_text())
    old = proposal['future_handle_directory']
    argv = [x.replace(old, str(ATTEMPT)) for x in proposal['observation_argv']]
    helper = Path(proposal['helper']['path'])
    roots = [Path('/usr/bin/strace'), Path('/usr/bin/bwrap'), helper]
    pending = roots[:]
    evidence = {}
    bindings = []
    while pending:
        original = pending.pop(0)
        resolved = original.resolve(strict=True)
        if str(resolved) in evidence:
            continue
        row = elf(resolved)
        evidence[str(resolved)] = row
        for search in row['embedded_library_search_paths']:
            search['host_directories_exist'] = [Path(p).exists() for p in search['value'].split(':')]
            search['namespace_mount_selected'] = False
            if any(search['host_directories_exist']):
                raise ValueError('existing_embedded_search_path_requires_explicit_selection_review')
        if row['interpreter']:
            dependency = Path(row['interpreter'])
            bindings.append(dict(parent=str(resolved), source='PT_INTERP',
                                 native_reference=str(dependency), resolved_path=str(dependency.resolve(strict=True))))
            pending.append(dependency)
        for name in row['needed']:
            dependency = Path('/usr/lib/x86_64-linux-gnu') / name
            if not dependency.is_file():
                raise ValueError('needed_library_unavailable:' + name)
            bindings.append(dict(parent=str(resolved), source='DT_NEEDED', native_reference=name,
                                 original_path=str(dependency), resolved_path=str(dependency.resolve(strict=True))))
            pending.append(dependency)
    runtime = [row['file'] for key, row in sorted(evidence.items())]
    cache = pin('/etc/ld.so.cache')
    files = [pin(PRIOR / 'retained/fixture' / name)
             for name in ('ERR3487613', 'ERR3487613.fasta', 'offline.kfg')]
    expected = {
        'ERR3487613': (35175, '266e59ba8a5033a084ddb95ab4518fe1c2e71a96e1fc20bb0b959a88c15567d7'),
        'ERR3487613.fasta': (6442, '165c749d742d0436d0482139fa0d734f7c4fdc7d9b428e73efaacaac416a97c8'),
        'offline.kfg': (201, 'ab65e06f45d7b49f187f3f79f963e909b8b20e2e2aa2d46b416cc40a9fe2c8fd'),
    }
    for row in files:
        assert (row['size_bytes'], row['sha256']) == expected[Path(row['path']).name]
    assert pin(helper) == proposal['helper']
    namespace_env = {}
    for index, value in enumerate(argv):
        if value == '--setenv':
            namespace_env[argv[index + 1]] = argv[index + 2]
    selected = dict(
        schema='blast_vdb_native_observation_selection_v1', proposal_pin=pin(PRIOR / 'NATIVE_OBSERVATION_SELECTION_PROPOSAL.json'),
        attempt_path=str(ATTEMPT), observation_argv=argv,
        observation_cwd=str(ATTEMPT / 'temporary/native_observation'),
        observation_environment={'LC_ALL': 'C', 'TMPDIR': str(ATTEMPT / 'temporary/native_observation/tmp'),
                                 'TMP': str(ATTEMPT / 'temporary/native_observation/tmp'),
                                 'TEMP': str(ATTEMPT / 'temporary/native_observation/tmp')},
        helper_argv=proposal['helper_argv_in_selected_namespace'], helper_environment=namespace_env,
        helper_cwd='/work', table_has_actual_tabs=True,
        selector_basis='source_derived_expectation_not_observed_helper_output',
        selected_inputs=files, helper_pin=pin(helper), observation_facility_pins=[pin(p) for p in roots[:2]],
        runtime_pins=runtime + [cache], elf_dependency_evidence=list(evidence.values()),
        elf_dependency_bindings=bindings,
        runtime_selection_basis='ELF_PT_INTERP_and_DT_NEEDED_recursive_system_multiarch_resolution_plus_selected_loader_cache',
        namespace_file_bindings=[dict(host_path=str(helper), namespace_path='/native/blast_vdb_cmd'),
                                 dict(host_path=str(PRIOR / 'retained/fixture/ERR3487613'), namespace_path='/input/ERR3487613'),
                                 dict(host_path=str(PRIOR / 'retained/fixture/offline.kfg'), namespace_path='/config/offline.kfg')],
        permitted_system_interfaces=['/dev/null', '/dev/urandom', '/dev/random', '/proc/self/status',
                                     '/proc/self/attr/current', '/proc/self/uid_map', '/proc/self/gid_map',
                                     '/proc/self/setgroups', '/proc/self/mountinfo',
                                     '/proc/sys/kernel/overflowuid', '/proc/sys/kernel/overflowgid'],
        permitted_system_interfaces_basis='explicit_finite_observation_setup_interfaces_for_root_review_not_scientific_content',
        undeclared_reads='retain_as_evidence_gap_no_additional_acquisition_or_mount',
        policy={'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'swap_bytes': 0, 'wall_seconds': None},
        support='supporting_selected_entry_extraction_no_search_no_scores_no_production_integration')
    (PACKET / 'SELECTED_REQUEST.json').write_text(json.dumps(selected, indent=2) + '\n')
    cmd = ['python3', str(RUNNER.relative_to(REPO) / 'run_checks.py'), 'launch', ATTEMPT.name,
           '--mode', 'check', '--dependencies-from', str(RUNNER.relative_to(REPO) / 'check005/dependencies'),
           '--test', 'test_blast_vdb_native_observation_661.py::test_selected_native_observation',
           '--support-tree', str(PACKET.relative_to(REPO)),
           '--support-tree', str(PRIOR.relative_to(REPO) / 'retained'),
           '--existing-native-executable', str(helper)]
    for row in runtime + [cache]:
        if row['path'] != str(helper):
            cmd.extend(['--native-library', row['path']])
    (PACKET / 'LAUNCH_COMMAND.sh').write_text(shlex.join(cmd) + '\n')
    sources = [REPO / name for name in ('gene_annotation_episode/native_lifecycle.py',
               'gene_annotation_episode/local_jobs.py', 'gene_annotation_episode/_local_job_worker.py',
               'gene_annotation_episode/blast_vdb_inputs.py')]
    sources += [RUNNER / 'run_checks.py', RUNNER / 'bounded_entry.py', Path(__file__).resolve()]
    (PACKET / 'SOURCE_PINS_BEFORE.json').write_text(json.dumps([pin(p) for p in sources], indent=2) + '\n')
    print(json.dumps({'selected_request': str(PACKET / 'SELECTED_REQUEST.json'),
                      'runtime_files': len(runtime), 'launch_command': shlex.join(cmd),
                      'source_pins': [pin(p) for p in sources]}, indent=2))


if __name__ == '__main__':
    main()
