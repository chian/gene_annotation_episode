"""Actual standalone scientific task entry and optional native timing metadata.

Caller credit values are explicit engineering inputs. No scientific conclusion,
provider, native operation, controller or Episode iteration is fabricated.
"""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]
ROOT=Path(__file__).resolve().parents[1]
AXIS=ROOT.name.upper()
def module(name):
    return import_module(PACKAGE+'.'+name)


@pytest.mark.parametrize('credit',[2.5,{'mode':'annotation_axis_credit','arms':[]}])
@pytest.mark.parametrize('timing',[False,True])
def test_actual_standalone_scientific_constructor_preserves_caller_credit_and_timing(tmp_path,credit,timing):
    library=module('sequence_homology_evidence_library').SequenceHomologyEvidenceLibrary.freeze(
        tmp_path/'scientific-process-library',source=ROOT.parents[3]/'research/slotted_process_library/publications/2026-10-24-001')
    tools_library=module('scientific_tool_library').ScientificToolLibrary.freeze(tmp_path/'tool-library',catalog=[])
    calls=[]
    class EngineeringProjector:
        def __call__(self,store,scope,**arguments):
            calls.append(deepcopy(arguments))
            return {'credit':deepcopy(credit),'proposed_annotations':[],'comparisons':[]}

        def as_record(self):
            return {'version':'standalone_engineering_credit_fixture_v1',
                'meaning':'Explicit caller test operand; no executed scientific progress.',
                'credit_input':deepcopy(credit)}
    projector=EngineeringProjector()
    def unused(*args,**kwargs):
        pytest.fail('Constructor and projection must not select provider, controller or native work')
    with module('state').Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        scope=store.validate_scope()
        timing_binding=module('native_timing_information').NativeTimingInformation(1) if timing else None
        Binding=module('sequence_homology_evidence.episode').SequenceHomologyEvidenceEpisode
        Workflow=module('runtime').Workflow
        workflow=Workflow(store,module('tools').ToolRegistry(store,clients=SimpleNamespace()),
            SimpleNamespace(complete=unused),tmp_path/'workflow','actual-scientific-entry',unused,projector,
            root_role='sequence_homology_evidence',native_timing_information=timing_binding,
            initial_known_record_refs=[],
            episode_binding_factories=(lambda services:Binding(services,library=library,
                tool_library=tools_library,child_roles=('sequence_homology_evidence',)),))
        binding=workflow.sequence_homology_evidence_binding
        schema={'type':'object','properties':{'constructor_input_supplied':{'type':'boolean','description':'Whether the caller supplied this engineering-only report form.'}},'required':['constructor_input_supplied'],'additionalProperties':False}
        contract=module('runtime').TypedReportContract('Return engineering fixture metadata',schema,lambda *_:True)
        assignment={'selection':{'version':'sequence_homology_evidence_selection_v3',
            'evidence_axis':library.reference(AXIS),'thought_pattern':library.reference('P01'),'child_tool_info':[]},
            'evidence_refs':[],'constraints':{},'context':{}}
        if AXIS=='A106':
            assignment['context']['evidence_task']={'version':'evidence_axis_task_v1',
                'kind':'whole_axis_findings','evidence_axis':AXIS,'credit_unit':1}
        with pytest.raises(module('domain').ContractError,match='scientific_parent_invocation_required'):
            binding.prepare_assignment(None,'sequence_homology_evidence',assignment,scope,'no-parent')
        # Explicit preparation input is not claimed to be a journal commission.
        parent=module('episode_bindings').BindingContext(workflow.run_id,'preparation','annotation',
            (('annotation','preparation'),),scope,{}, {'message':{'scope':scope,'episode_assignment':{}}})
        prepared=binding.prepare_invocation(parent,'sequence_homology_evidence',assignment,scope,'explicit:prepare',
            invocation={'objective':'Characterize actual standalone credit input','purpose':contract.decision,
                'report_schema':schema,'initial_report':{'constructor_input_supplied':True}})
        episode=workflow.build('sequence_homology_evidence','standalone','Characterize actual standalone credit input',
            scope,contract=contract,initial={'constructor_input_supplied':True},episode_assignment=prepared['assignment'],sequence_homology_evidence=prepared['sequence_homology_evidence'])
        source=episode.source
        assert type(source) is Binding.decision_source_type
        assert source.path==(('sequence_homology_evidence','standalone'),)
        context=workflow.binding_context(source)
        binding.validate_context(context)
        assert workflow.scientific_projector_for_context(context) is projector
        view=workflow.source_credit_view(source)
        assert view['credit']==credit
        if timing:
            assert view['monitoring_information_credit']==0
            assert view['monitoring_information_binding']==timing_binding.as_record()
        else:
            assert 'monitoring_information_credit' not in view
        assert calls and all(arguments=={} for arguments in calls)
        for table in ('runtime_actions','runtime_observations','runtime_model_calls','tool_operations'):
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0
