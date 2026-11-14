"""Actual iterator owners and source identity; no science or provider execution.

The byte-perturbation cases explicitly control only source reads. They never
change application files, saved descriptors, authority readers or science.
"""
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path

import pytest


AXIS = 'gene_annotation_episode.episodic_workflow.root.a105'
CANONICAL = 'gene_annotation_episode.episodic_workflow.root.method_loop'
KEY_PREFIX = 'gene_annotation_episode/episodic_workflow/root/method_loop/'
ITERATOR_FILES = {
    '__init__.py', 'archive.py', 'binding.py', 'communication.py', 'durable.py',
    'durable_worker.py', 'episode.py', 'identities.py', 'independent.py',
    'reconstruction.py', 'runtime.py', 'suspension.py',
}


APPLICATION_FILES = {
    'gene_annotation_episode/__init__.py',
    'gene_annotation_episode/episodic_workflow/__init__.py',
    'gene_annotation_episode/episodic_workflow/root/__init__.py',
    'gene_annotation_episode/domain.py',
    'gene_annotation_episode/acquisition.py',
    'gene_annotation_episode/public_configuration.py',
    'gene_annotation_episode/form_reference_validation.py',
    'gene_annotation_episode/episode_bindings.py',
    'gene_annotation_episode/schema_information_text.py',
    'gene_annotation_episode/schema_support.py',
    'gene_annotation_episode/boundary_validation.py',
    'gene_annotation_episode/journal_metadata.py',
    'gene_annotation_episode/episodic_workflow/root/communication.py',
    'gene_annotation_episode/episodic_workflow/root/episode_contract_information.py',
    'gene_annotation_episode/episodic_workflow/root/episode_journal.py',
    'gene_annotation_episode/episodic_workflow/root/provider_errors.py',
    'gene_annotation_episode/episodic_workflow/root/receiving_context.py',
    'gene_annotation_episode/episodic_workflow/root/task_action_units.py',
    'gene_annotation_episode/episodic_workflow/root/task_values.py',
    'gene_annotation_episode/episodic_workflow/root/execution_timing.py',
    'gene_annotation_episode/episodic_workflow/root/boundary_validation.py',
}

def _sources():
    return import_module(AXIS + '.implementation_sources')


@pytest.fixture
def descriptor_binding(tmp_path):
    # Real empty, validated research/tool libraries are sufficient to identify
    # an implementation. No option, tool, scientific finding or grade is invented.
    process = import_module(AXIS + '.scientific_process_library')
    tools = import_module(AXIS + '.scientific_tool_library')
    records = import_module(AXIS + '.scientific_process_records')
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'index.json').write_text(json.dumps({
        'format': process.SOURCE_FORMAT, 'status': 'Empty source identity fixture',
        'slots': [{'slot': slot, 'catalog': slot + '.json', 'count': 0} for slot in records.SLOTS],
        'entries': [],
    }), encoding='utf-8')
    (source / 'option_sources.json').write_text(json.dumps({
        'meaning': 'No scientific options or evidence in this fixture', 'rows': [],
    }), encoding='utf-8')
    library = process.ScientificProcessLibrary.freeze(tmp_path / 'library', source=source)
    tool_library = tools.ScientificToolLibrary.freeze(tmp_path / 'tools', catalog=[])
    episode = import_module(AXIS + '.scientific_process.episode').ScientificProcessEpisode
    # The original reconstruction code also uses factory(None) for descriptors.
    # No service method is invoked or supplied through a substitute object.
    return episode(None, library=library, tool_library=tool_library,
                   child_roles=('scientific_process',))


def test_maps_include_actual_canonical_files_and_preserve_private_keys():
    sources = _sources()
    root = Path(sources.__file__).resolve().parent
    loop = Path(import_module(CANONICAL).__file__).resolve().parent
    expected_shared = {KEY_PREFIX + name: loop / name for name in ITERATOR_FILES}
    expected_shared.update({name: loop.parents[3] / name for name in APPLICATION_FILES})
    for select, excluded in ((sources.independent_source_files, {'tests', '__pycache__'}),
                             (sources.scientific_source_files, {'tests'})):
        expected_private = {str(p.relative_to(root)): p for p in root.rglob('*.py')
                            if not excluded.intersection(p.relative_to(root).parts)
                            and p.relative_to(root).parts[0] != 'method_loop'}
        actual = select()
        assert actual == expected_private | expected_shared
        assert all(path.is_file() for path in actual.values())
        assert actual['scientific_process/task.py'] == root / 'scientific_process/task.py'
        assert actual['implementation_sources.py'] == root / 'implementation_sources.py'
        assert not any(key.startswith('method_loop/') for key in actual)
        assert len({p for k, p in actual.items() if k.startswith(KEY_PREFIX)}) == 12


def test_both_original_digest_algorithms_and_configuration_are_preserved(descriptor_binding):
    sources = _sources()
    independent = import_module(AXIS + '.independent_execution')
    stream = hashlib.sha256()
    for name, path in sorted(sources.independent_source_files().items()):
        stream.update(name.encode('utf-8') + b'\0')
        stream.update(hashlib.sha256(path.read_bytes()).digest())
    assert independent.implementation_sha256() == stream.hexdigest()
    mapping = {name: hashlib.sha256(path.read_bytes()).hexdigest()
               for name, path in sources.scientific_source_files().items()}
    scientific = hashlib.sha256(json.dumps(mapping, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    record = descriptor_binding.as_record()
    assert record['implementation_sha256'] == scientific
    assert record['binding_id'] == 'scientific_process'
    assert record['configuration'] == {
        'library': descriptor_binding.library.as_record(),
        'tool_library': descriptor_binding.tool_library.as_record(),
        'child_roles': ['scientific_process'],
    }


@pytest.mark.parametrize('selected,changes_identity', [
    ('canonical_iterator', True), ('private_science', True), ('inactive_private_iterator', False),
    ('canonical_error', True), ('canonical_context', True), ('canonical_helper', True),
])
def test_source_byte_changes_follow_executing_owners(descriptor_binding, monkeypatch,
                                                    selected, changes_identity):
    sources = _sources()
    independent = import_module(AXIS + '.independent_execution')
    private = Path(sources.__file__).resolve().parent
    canonical = Path(import_module(CANONICAL).__file__).resolve().parent
    target = {'canonical_error': canonical.parent / 'communication.py',
              'canonical_context': canonical.parent / 'receiving_context.py',
              'canonical_helper': canonical.parent / 'task_values.py',
              'canonical_iterator': canonical / 'episode.py',
              'private_science': private / 'scientific_process/task.py',
              'inactive_private_iterator': private / 'method_loop/episode.py'}[selected]
    before_runtime = independent.implementation_sha256()
    before_record = deepcopy(descriptor_binding.as_record())
    read_bytes = Path.read_bytes

    def changed_bytes(path):
        raw = read_bytes(path)
        return raw + b'\n# controlled source identity perturbation\n' if path.resolve() == target else raw

    monkeypatch.setattr(Path, 'read_bytes', changed_bytes)
    assert (independent.implementation_sha256() != before_runtime) is changes_identity
    after = descriptor_binding.as_record()
    assert (after['implementation_sha256'] != before_record['implementation_sha256']) is changes_identity
    assert after['configuration'] == before_record['configuration']
    assert after['version'] == before_record['version']
    if changes_identity:
        compatible = import_module(AXIS + '.episode_composition').scientific_binding_compatible
        assert not compatible(before_record, after)


def test_missing_canonical_source_does_not_fall_back_to_private_copy(descriptor_binding, monkeypatch):
    independent = import_module(AXIS + '.independent_execution')
    target = Path(import_module(CANONICAL).__file__).resolve().parent / 'episode.py'
    read_bytes = Path.read_bytes

    def unavailable(path):
        if path.resolve() == target:
            raise FileNotFoundError(str(path))
        return read_bytes(path)

    monkeypatch.setattr(Path, 'read_bytes', unavailable)
    with pytest.raises(FileNotFoundError):
        independent.implementation_sha256()
    with pytest.raises(FileNotFoundError):
        descriptor_binding.as_record()


def test_source_join_preserves_private_keys_and_excludes_only_inactive_loop(tmp_path):
    sources = _sources()
    private = tmp_path / 'private'
    names = ('science.py', '__pycache__/generated.py', 'method_loop/episode.py',
             'method_loop_elsewhere.py', 'science/method_loop_reference.py')
    for name in names:
        path = private / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# source-map fixture\n', encoding='utf-8')
    # This is the actual source-map join over real fixture files. The callers'
    # distinct original filters are independently checked by the source audit.
    actual = sources._with_canonical_iterator(private, (private / name for name in names))
    retained = set(names) - {'method_loop/episode.py'}
    assert set(actual) == retained | {KEY_PREFIX + name for name in ITERATOR_FILES} | APPLICATION_FILES
    assert all(actual[name] == private / name for name in retained)
    assert all(path.is_file() for path in actual.values())


def test_real_private_iterator_values_have_canonical_bases():
    canonical = import_module(CANONICAL)
    runtime = import_module(AXIS + '.runtime')
    records = import_module(AXIS + '.scientific_process.published_evidence_assessment.'
        'evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.task_records')
    for owner in (runtime, records):
        assert owner.SourceEnd is canonical.SourceEnd
        assert owner.ReportRedelivery is canonical.ReportRedelivery
        assert owner.Episode is canonical.Episode
        assert issubclass(owner.Record, canonical.ClosedRecord)
    assert issubclass(runtime.TypedReportContract, canonical.ReportContract)
    assert runtime.Record({'status': 'unavailable'}).as_record() == {'status': 'unavailable'}
