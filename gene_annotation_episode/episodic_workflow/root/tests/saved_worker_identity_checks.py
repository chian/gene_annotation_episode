"""Finite record-reader controls; no native computation or replay is started.

RNA, genomic job and flux records are exact retained fixtures. Frozen NMF and
genomic worker intents are explicit engineered schema inputs, not execution
evidence. Current variants change only the declared owner and its source pins.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

OLD = 'gene_annotation_episode.'
NEW = 'gene_annotation_episode.episodic_workflow.root.library.'
FAMILIES = ('rna_job', 'genomic_job', 'flux_job', 'nmf_intent', 'genomic_intent')
ORIGINAL_SCENARIOS = ('historical_roundtrip', 'unknown_owner_rejected', 'historical_control_rejected')
SCENARIOS = (*ORIGINAL_SCENARIOS, 'current_roundtrip', 'mixed_owner_rejected', 'current_control_rejected')
CASES = tuple(family + ':' + scenario for family in FAMILIES for scenario in SCENARIOS)
ORIGINAL_CASES = tuple(family + ':' + scenario for family in FAMILIES for scenario in ORIGINAL_SCENARIOS)


def _fixture(name):
    return json.loads((Path(__file__).parent / 'fixtures/saved_worker_identity' / (name + '.json')).read_bytes())


def _pin(path):
    # Engineered intent validation does not read this file or claim its presence.
    return {'path': path, 'sha256': hashlib.sha256(path.encode()).hexdigest(), 'size_bytes': len(path)}


def _engineered(family):
    root = '/engineered-original-worker'
    stem = 'expression_nmf_result_worker' if family == 'nmf_intent' else 'genomic_overlap_result_worker'
    plan = {'directory': root}
    source_root = root + '/source_snapshot/'
    sources = [source_root + 'gene_annotation_episode/' + stem + '.py']
    if family == 'genomic_intent':
        sources += [source_root + 'gene_annotation_episode/' + name + '.py' for name in
                    ('__init__', 'genomic_overlap_contracts', 'genomic_overlap_inputs',
                     'genomic_overlap_calculations', 'genomic_overlap_result_views', 'native_genomic_overlap_contracts')]
    environment = dict(PYTHONPATH=source_root[:-1], PYTHONHOME='/engineered-python',
                       PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
                       TMPDIR=root, TMP=root, TEMP=root, XDG_CACHE_HOME=root + '/cache',
                       PIP_CACHE_DIR=root + '/cache/pip')
    intent = dict(version=('expression_nmf' if family == 'nmf_intent' else 'genomic_overlap') + '_worker_intent_v1',
                  plan=deepcopy(plan), policy={'memory_bytes': 5368709120, 'scratch_bytes': 4294967296},
                  command=[root + '/runtime/python', '-B', '-S', '-m', OLD + stem, root + '/plan.json'],
                  environment=environment, source_pins=[_pin(path) for path in sorted(sources)],
                  interpreter=_pin(root + '/runtime/python'))
    if family == 'nmf_intent':
        intent.update(dependencies=[{'files': [_pin('/engineered-dependency/package.py')]}],
                      python_version='engineered original record', python_home='/engineered-python',
                      runtime_files=[_pin('/engineered-python/lib/original.py')])
    return intent, plan


def _current_sources(value, family):
    if family == 'rna_job':
        value['native_rna_structure']['software']['worker_module'] = NEW + 'native_rna_structure_worker'
        value['argv'][3] = NEW + 'native_rna_structure_worker'
        # Preserve the original explicit canonical software argument; do not
        # ask the candidate request compiler to manufacture the test oracle.
        software_argument = value['argv'].index('--software-json') + 1
        value['argv'][software_argument] = json.dumps(value['native_rna_structure']['software'],
            sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    elif family == 'genomic_job':
        software = value['native_genomic_overlap']['software']
        software['driver_module'] = NEW + 'native_genomic_overlap_driver'
        for pin in software['implementation_files']:
            pin['module'] = NEW + pin['module'].removeprefix(OLD)
        value['argv'][3] = NEW + 'native_genomic_overlap_driver'
    elif family == 'flux_job':
        software = value['native_flux_balance']['software']
        base = software['module_root'] + '/gene_annotation_episode/'
        for pin in software['implementation_files']:
            if pin['path'].startswith(base) and Path(pin['path']).name in {
                'flux_balance_contracts.py', 'native_flux_balance_contracts.py',
                'native_flux_balance_storage.py', 'native_flux_balance_cobra_glpk.py', 'native_flux_balance_driver.py'}:
                pin['path'] = base + 'episodic_workflow/root/library/' + Path(pin['path']).name
        value['argv'][4] = NEW + 'native_flux_balance_driver'
    else:
        value['command'][4] = NEW + value['command'][4].removeprefix(OLD)
        for pin in value['source_pins']:
            if not pin['path'].endswith('/__init__.py'):
                pin['path'] = pin['path'].replace('/gene_annotation_episode/', '/gene_annotation_episode/episodic_workflow/root/library/', 1)
        value['source_pins'].sort(key=lambda pin: pin['path'])


def check(case, modules):
    family, scenario = case.split(':')
    assert family in FAMILIES and scenario in SCENARIOS
    if family.endswith('_intent'):
        value, plan = _engineered(family)
        validate = lambda supplied: modules[family]._validate_intent(supplied, plan)
    else:
        value = _fixture(family)
        method = {'rna_job': 'validate_rna_structure_requested_job',
                  'genomic_job': 'validate_genomic_overlap_requested_job',
                  'flux_job': 'validate_flux_balance_requested_job'}[family]
        validate = ((lambda supplied: getattr(modules[family], method)(supplied, historical=True))
                    if family == 'flux_job' else (lambda supplied: getattr(modules[family], method)(supplied)))
    if scenario.startswith('current') or scenario == 'mixed_owner_rejected':
        _current_sources(value, family)
    if scenario == 'unknown_owner_rejected':
        if family == 'rna_job':
            value['native_rna_structure']['software']['worker_module'] = OLD + 'unassigned_worker'
        elif family == 'genomic_job':
            value['native_genomic_overlap']['software']['driver_module'] = OLD + 'unassigned_driver'
        elif family == 'flux_job':
            value['argv'][4] = OLD + 'unassigned_driver'
        else:
            value['command'][4] = OLD + 'unassigned_worker'
    elif scenario == 'mixed_owner_rejected':
        if family in ('rna_job', 'genomic_job'):
            value['argv'][3] = value['argv'][3].replace(NEW, OLD, 1)
        elif family == 'flux_job':
            value['argv'][4] = value['argv'][4].replace(NEW, OLD, 1)
        else:
            value['command'][4] = value['command'][4].replace(NEW, OLD, 1)
    elif scenario.endswith('control_rejected'):
        if family.endswith('_job'):
            value['argv'][-1] += '-foreign-original'
        else:
            value['interpreter']['path'] += '-foreign-original'
    frozen = deepcopy(value)
    if scenario.endswith('roundtrip'):
        assert validate(value) == frozen
    else:
        try:
            validate(value)
        except ValueError:
            pass
        else:
            raise AssertionError('changed original identity/control was accepted: ' + case)
    assert value == frozen, case
