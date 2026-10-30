"""Actual scripted parent presentation, full child TASK and selective numbers."""
import asyncio
from copy import deepcopy

import pytest

from gene_annotation_episode.literature_controlled_response_prompt import CONTROLLED_RESPONSE_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from literature_controlled_response_worker_fixture_095 import make_case, run_case


def broad_numeric_definition(fixture):
    fixture.text_measurement('protein_condition1', 'Protein signal 127.438234 nmol/min.', '127.438234')
    phrase = 'Source confidence interval [121.135791, 133.246802] nmol/min; confidence 93%; count 73 biological preparations.'
    fixture.append(phrase)
    witness = fixture.witness(phrase,tagged=False)
    interval = {'witness':witness}
    for side,token in [('lower','121.135791'),('upper','133.246802')]:
        interval[side+'_start']=phrase.index(token);interval[side+'_end']=phrase.index(token)+len(token)
    uncertainty = fixture.args['arms']['protein_condition1']['reported_uncertainty']
    uncertainty.update(statistic=fixture.interp('ci','confidence interval'),magnitude=None,interval=interval,
        confidence_level=fixture.witness('93%',tagged=False),count=fixture.number(phrase,'73'),
        unit_relationship=fixture.interp('same_as_response','nmol/min'),
        repetition_basis=fixture.interp('biological_preparations','biological preparations'))
    # An authenticated broad meaning must not undo a derived-only numerical
    # request by quoting its hidden uncertainty/response values back as a label.
    for arm in fixture.args['arms'].values():
        if arm is None:continue
        meaning = arm['endpoint']; tagged = fixture.witness(phrase)
        meaning.update(label=phrase,witnesses=[deepcopy(tagged)],canonical_witness=deepcopy(tagged),
            canonical_correspondence={'value':'same','witnesses':[deepcopy(tagged)]})


@pytest.mark.parametrize('raw',[False,True])
def test_requested_raw_uncertainty_is_retained_and_derived_only_does_not_expand_it(tmp_path,raw):
    store,case = make_case(tmp_path/'state',alter_fixture=broad_numeric_definition,
        names=['protein_condition1_response' if raw else 'controlled_response_difference'],
        views=['native_raw' if raw else 'final'],
        keys=['raw:protein_condition1:primary' if raw else 'final:controlled_response_difference'])
    try:
        _,provider,_ = asyncio.run(run_case(store,case,tmp_path/'run',child_actions=3))
        child = [text for state,text in zip(provider.contexts,provider.presented) if 'literature_assignment' in state]
        assert child and all(CONTROLLED_RESPONSE_TASK in text for text in child)
        own_next = [text for state,text in zip(provider.contexts,provider.presented)
            if 'literature_assignment' in state and isinstance((state.get('last_local_outcome') or {}).get('result'),dict)
            and 'component_keys' in state['last_local_outcome']['result']]
        assert len(own_next)==1
        rendered = provider.presented[-1]
        assert REFERENCE_PARENT_TASK in rendered and CONTROLLED_RESPONSE_TASK not in rendered
        for actual_text in [rendered,*own_next]:
            steering = actual_text.split('\n\nSTEERING\n',1)[1]
            assert 'Requested controlled response components' in steering
            assert 'Construct: protein X.' in steering
            for hidden in ('sheet_ref','component_key','payload_sha256','canonical_witness_location',
                    'literature_controlled_response_return_bindings','raw:protein_condition1:primary',
                    'final:controlled_response_difference'):
                assert hidden not in steering
            for token in ('127.438234','0.121135791','0.133246802','0.93','73'):
                assert (token in steering)==raw
            for token in ('121.135791','133.246802'):
                assert token not in steering
            if raw:
                assert 'biological_preparations' in steering and 'ci' in steering
            else:
                assert 'source-bound meaning retained for scoped access' in steering
        assert all('raw:protein_condition1:primary' not in text.split('\n\nSTEERING\n',1)[0]
            and 'final:controlled_response_difference' not in text.split('\n\nSTEERING\n',1)[0] for text in child)
    finally:store.close()


@pytest.mark.parametrize('unknown_response',[False,True])
def test_actual_next_decision_preserves_independent_source_uncertainty_unit(tmp_path,unknown_response):
    from test_literature_controlled_response_uncertainty_units_v3 import configure_uncertainty_units
    store,case=make_case(tmp_path/'state',names=['protein_condition1_response'],views=['native_raw'],
        alter_fixture=lambda fixture:configure_uncertainty_units(fixture,unknown_response=unknown_response))
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run',child_actions=3))
        texts=[text for state,text in zip(provider.contexts,provider.presented)
            if 'literature_assignment' in state and isinstance((state.get('last_local_outcome') or {}).get('result'),dict)
            and 'component_keys' in state['last_local_outcome']['result']]
        texts.append(provider.presented[-1]);assert len(texts)==2
        for text in texts:
            steering=text.split('\n\nSTEERING\n',1)[1]
            assert '| magnitude_and_interval_unit | uM/min |' in steering
            assert '0.121135791' in steering and '0.136246802' in steering
            if not unknown_response:assert '| unit | nmol/min |' in steering
        parent=next(state for state in provider.contexts if state.get('child_reports'))
        row=parent['child_reports'][0]['requested_response'][0]
        assert row['reported_uncertainty_unit']=='uM/min'
        assert row['cell']['unit']==(None if unknown_response else 'umol/min')
        assert row['native_reading']['unit']==(None if unknown_response else 'nmol/min')
    finally:store.close()
