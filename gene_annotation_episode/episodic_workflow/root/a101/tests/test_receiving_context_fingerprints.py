"""Real configurable bindings with independent original source framing + four operands."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import pytest
from .receiving_context_controls import own, AXIS, AXIS_ROOT, REPOSITORY, CASES, EXTERNAL
from .test_actual_private_registry import constructed
from .test_private_descriptor_reopening import compose


@pytest.fixture(scope='module')
def owners(constructed):
    _,_,_,bindings,_ = constructed
    services = bindings[0].services
    result = {b.binding_path:b for b in bindings}
    for prefix in ('','scientific_process.'):
        for binding in own(prefix+'published_evidence_assessment.episode').create_binding_tree(services):
            result[binding.binding_path] = binding
        monitor = own(prefix+'execution_progress_assessment.episode').MonitorEpisode(services)
        result[monitor.binding_path] = monitor
    for row in CASES['records']:
        if row['family'] == 'a101_resource_raw_home_ordered_sources':
            home = row['home']; binding = own(home.replace('/','.')+'.episode').ResourceEpisode(services)
            assert binding.binding_path == home
            result[home] = binding
    assert set(r['home'] for r in CASES['records']) <= set(result)
    return result


def framing(row, profile=None):
    home = AXIS_ROOT / row['home']; family = row['family']
    external = [(key,(REPOSITORY/key).read_bytes()) for key in EXTERNAL]
    if family == 'scientific_relative_key_hex_map':
        values = {str(p.relative_to(AXIS_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in AXIS_ROOT.rglob('*.py') if 'tests' not in p.parts}
        assert not set(values).intersection(EXTERNAL)
        values.update({key:hashlib.sha256(raw).hexdigest() for key,raw in external})
        return own('scientific_process_records').scientific_digest(values)
    if family == 'a106_literature_relative_name_raw_axis':
        digest = hashlib.sha256()
        for path in sorted(AXIS_ROOT.rglob('*')):
            if 'tests' in path.relative_to(AXIS_ROOT).parts or not path.is_file(): continue
            if path.suffix not in {'.py','.json'}: continue
            digest.update(path.relative_to(AXIS_ROOT).as_posix().encode('utf8'))
            digest.update(path.read_bytes())
        for key,raw in external: digest.update(key.encode('utf8')); digest.update(raw)
        return digest.hexdigest()
    raw = b''.join(p.read_bytes() for p in sorted(home.glob('*.py')))
    if family == 'a101_literature_raw_home_prompt':
        raw += (AXIS_ROOT/'library/literature_investigation_prompt.py').read_bytes()
    elif family == 'monitor_raw_home_two_helpers':
        for name in ('monitor_prompt.py','progress_information_credit.py'):
            raw += (AXIS_ROOT/'library'/name).read_bytes()
    elif family == 'a101_resource_raw_home_ordered_sources':
        names = ('a101_resource_implementation.py','library/homology_query.py',
                 *CASES['resource_sources'], 'homology_job_submission/yield_estimator.py', 'homology_job_monitoring/yield_estimator.py', 'homology_result_acquisition/yield_estimator.py', 'resource_information.py',
                 'resource_records.py','launch_instructions.py')
        for name in names: raw += (AXIS_ROOT/name).read_bytes()
        if profile is not None:
            for name in ('composition_information.py','schema_information_text.py'):
                raw += (AXIS_ROOT/name).read_bytes()
    else: raise AssertionError('unaccounted original descriptor family: '+family)
    return hashlib.sha256(raw+b''.join(raw for _,raw in external)).hexdigest()


@pytest.mark.parametrize('row', CASES['records'], ids=lambda row:row['home'])
def test_every_configured_hash_uses_original_framing_and_four_external_inputs(owners,row):
    binding = owners[row['home']]
    assert binding.as_record()['implementation_sha256'] == framing(row)


if AXIS == 'a101':
    @pytest.mark.parametrize('row', [r for r in CASES['records'] if r['family']=='a101_resource_raw_home_ordered_sources'],ids=lambda row:row['home'])
    def test_resource_information_profile_keeps_conditional_original_inputs(owners,row):
        profile = own('composition_information').CONTRACT_INFORMATION_PROFILE
        original = owners[row['home']]
        binding = type(original)(original.services,contract_information_profile=profile)
        assert binding.as_record()['configuration']['contract_information_profile'] == profile
        assert binding.as_record()['implementation_sha256'] == framing(row,profile)


@pytest.mark.parametrize('key', EXTERNAL)
@pytest.mark.parametrize('family', sorted({r['family'] for r in CASES['records']}))
def test_each_external_input_changes_real_selected_binding_hash(owners,monkeypatch,key,family):
    row = next(r for r in CASES['records'] if r['family']==family)
    binding = owners[row['home']]; before = binding.as_record()['implementation_sha256']
    read = Path.read_bytes; target = REPOSITORY/key
    def changed(path):
        raw = read(path)
        return raw+b'\n# controlled fingerprint operand only\n' if path.resolve()==target.resolve() else raw
    # No filesystem/source mutation or replacement module/class. This controls
    # the actual method's byte input; scientific validation is not under test.
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_bytes',changed)
        observed = binding.as_record()['implementation_sha256']
        assert observed != before
        assert observed == framing(row)
    assert binding.as_record()['implementation_sha256'] == before


def independent_frame():
    digest = hashlib.sha256()
    files = sorted(AXIS_ROOT.rglob('*.py'))
    if AXIS == 'a101': files = [p for p in files if not {'tests','__pycache__'}.intersection(p.parts)]
    for path in files:
        digest.update(str(path.relative_to(AXIS_ROOT)).encode('utf8')+b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    for key in EXTERNAL:
        digest.update(key.encode('utf8')+b'\0')
        digest.update(hashlib.sha256((REPOSITORY/key).read_bytes()).digest())
    return digest.hexdigest()


def test_independent_execution_keeps_original_filters_and_nul_binary_framing():
    assert own('independent_execution').implementation_sha256() == independent_frame()


@pytest.mark.parametrize('key', EXTERNAL)
def test_independent_execution_each_external_operand_participates(monkeypatch,key):
    actual = own('independent_execution').implementation_sha256
    before = actual(); read = Path.read_bytes; target = REPOSITORY/key
    def changed(path):
        raw=read(path)
        return raw+b'\n# controlled operand\n' if path.resolve()==target.resolve() else raw
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_bytes',changed)
        assert actual() != before and actual() == independent_frame()
    assert actual() == before


def test_real_configured_descriptor_roundtrip_and_strict_hash_conflict(constructed,tmp_path):
    _,_,_,bindings,literature = constructed
    descriptors = [b.as_record() for b in (bindings[0],*literature)]
    (tmp_path/'actual-descriptors.json').write_text(json.dumps(descriptors,sort_keys=True)+'\n')
    rebuilt = compose(constructed,descriptors)
    assert [b.as_record() for b in rebuilt.bindings] == descriptors
    assert [type(b) for b in rebuilt.bindings] == [type(b) for b in (bindings[0],*literature)]
    saved = deepcopy(descriptors)
    for original in descriptors:
        changed=deepcopy(original); changed['implementation_sha256']='0'*64
        with pytest.raises(own('method_loop.durable').DurableExecutionError):
            compose(constructed,[changed])
    assert descriptors == saved


@pytest.mark.parametrize('change', ('binding_id','configuration'))
def test_configured_saved_descriptor_rejects_nonhash_identity_changes(constructed,change):
    *_,literature=constructed
    original=literature[0].as_record(); changed=deepcopy(original)
    if change=='binding_id': changed['binding_id']='foreign/unknown_episode'
    else: changed['configuration']['unrecognized_original_operand']=True
    with pytest.raises(own('method_loop.durable').DurableExecutionError): compose(constructed,[changed])
    assert literature[0].as_record()==original
