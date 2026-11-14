"""Original/current type, malformed-receipt and first-admission controls.

Required snapshots reconstruct the V11 source with current external dependencies.
They are not a historical native producer or a valid saved-result fixture.
"""
import asyncio
import hashlib
import importlib
from pathlib import Path
from types import ModuleType, SimpleNamespace

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104'
FAMILIES = (('native_hmmer_results', 'NativeHMMERResults', 'NativeHMMERResultRecords', 'NativeHMMERResultAcquisition', ('_action_directory', '_index', 'execute'), ()), ('native_blast_results', 'NativeBLASTResults', 'NativeBLASTResultRecords', 'NativeBLASTResultAcquisition', ('_action_directory', '_index', 'execute'), ()), ('native_blast_masking_results', 'NativeBLASTMaskingResults', 'NativeBLASTMaskingResultRecords', 'NativeBLASTMaskingResultAcquisition', ('_index', '_prior', 'execute'), ('_failure',)), ('native_blast_utility_results', 'NativeBLASTUtilityResults', 'NativeBLASTUtilityResultRecords', 'NativeBLASTUtilityResultAcquisition', ('_index', '_prior', 'execute'), ('_failure',)), ('native_blast_standard_database_results', 'StandardBLASTDatabaseResults', 'StandardBLASTDatabaseResultRecords', 'StandardBLASTDatabaseResultAcquisition', ('_index', 'execute'), ()), ('native_blast_database_results', 'NativeBLASTDatabaseResults', 'NativeBLASTDatabaseResultRecords', 'NativeBLASTDatabaseResultAcquisition', ('_index', 'execute'), ('_saved_failure',)), ('native_hmmer_preparation_results', 'NativeHmmerPreparationResults', 'NativeHmmerPreparationResultRecords', 'NativeHmmerPreparationResultAcquisition', ('_index', 'execute'), ()))
HOMES = ('execution_result_acquisition', 'scientific_process/execution_result_acquisition', 'hpc_work_planning/execution_result_acquisition', 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition', 'scientific_process/hpc_work_planning/execution_result_acquisition', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition')
ORIGINAL_HASHES = {'native_hmmer_results': '83bfa33d7a7032876df20c499c075d3273b65dfc39174824ab46abbaad20799d', 'native_blast_results': '7697374edb9f417055f524e87620af051f41a09acb3ac1bf1d1d1615d3d5c250', 'native_blast_masking_results': '5747e5e554a4272c5702dc9133bc04f045b72cc2be90b02493c6f03e1f1d5e45', 'native_blast_utility_results': 'f20c725113a1f6cddf93c09f477465323868ecda7a8403ddefa4dc668bd7cbdf', 'native_blast_standard_database_results': '0ea6a54c9243ad3e5f69b76344b5305a13fbb93f850459d7bb4384b88f199034', 'native_blast_database_results': '72f8b5df9b241ef18107003cf580081755e9fc2bcf549ac83553fcae26c7e0c3', 'native_hmmer_preparation_results': '91a3d7c2c5adce8a53947975448f1c6d39cbd76dd8d0e4f517aa574277bf0b46'}

def original(family):
    name = family[0]
    path = Path(__file__).parent / 'fixtures' / 'native_result_originals' / (name + '.py.txt')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_HASHES[name]
    module = ModuleType(PREFIX + '.tests._reconstructed_' + name)
    module.__package__ = PREFIX
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module, getattr(module, family[1])

def selected(home, family, phase):
    assert phase in {'baseline', 'connected'}
    if phase == 'baseline':
        module = importlib.import_module(PREFIX + '.' + family[0])
        return module, getattr(module, family[1])
    module = importlib.import_module(PREFIX + '.' + home.replace('/', '.') + '.' + family[0].removesuffix('_results') + '_result_acquisition')
    return module, getattr(module, family[3])

def exception_record(error):
    return {'module': type(error).__module__, 'type': type(error).__qualname__,
        'args': list(error.args), 'code': getattr(error, 'code', None),
        'detail': getattr(error, 'detail', None)}

def observe(cls, store, directory, family):
    from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
    from gene_annotation_episode.episodic_workflow.root.a104.a104_execution_bindings import install_primary_result_readers, install_preparation_result_readers
    selected_calls = []
    marker = ContractError('native_result_selected_action_control')
    def selected_action(*args):
        selected_calls.append(args)
        raise marker
    flags = ('native_blast_standard_database', 'native_blast_database', 'native_blast', 'native_hmmer_preparation')
    owner = SimpleNamespace(store=store, directory=directory, run_id='native-result-owner-control',
        resources={'selected': {name: {'selected': True} for name in flags}},
        _selected_result_action=selected_action)
    # Original installed return types authenticate the caller; no authentication port
    # or receipt validator is replaced by this fixture.
    install_primary_result_readers(owner)
    install_preparation_result_readers(owner)
    actor = cls(owner)
    setattr(owner, family[0], actor)
    # Use the actual return class constructor after assigning this Results object.
    paired = getattr(owner, family[0].removesuffix('_results') + '_returns', None)
    if paired is not None:
        setattr(owner, family[0].removesuffix('_results') + '_returns', type(paired)(owner))
    assert actor.owner is owner and actor.store is store
    before = list(store.db.iterdump())
    invalid = {'version': 'deliberately_invalid_receipt'}
    try:
        actor._validate_body(invalid, {})
    except (ValueError, TypeError, KeyError) as error:
        receipt = exception_record(error)
    else:
        raise AssertionError('original malformed receipt unexpectedly accepted')
    # A mismatched run is deliberately rejected by the original authentication
    # method before a selected action can be acquired. HMMER's original method
    # starts directly at the selected-action callback; preserve that distinction.
    context = SimpleNamespace(run_id='different-run', episode_id='unregistered',
        request={'message': {}}, role='results', path=(('results', 'control'),),
        scope={}, assignment={})
    try:
        asyncio.run(actor.execute(context, {}, 'execution.results.status', {}, 'control:1'))
    except (ValueError, TypeError, KeyError) as error:
        admission = exception_record(error)
        if family[0] == 'native_hmmer_results':
            assert error is marker
    else:
        raise AssertionError('original uncommissioned control unexpectedly executed')
    assert list(store.db.iterdump()) == before
    assert selected_calls == ([('unregistered', 'control:1', 'execution.results.status', {})]
        if family[0] == 'native_hmmer_results' else [])
    assert not list(directory.rglob('*'))
    return {'receipt': receipt, 'admission': admission, 'selected_calls': selected_calls,
        'owner_identity_preserved': True, 'store_unchanged': True, 'native_work_executed': False}
