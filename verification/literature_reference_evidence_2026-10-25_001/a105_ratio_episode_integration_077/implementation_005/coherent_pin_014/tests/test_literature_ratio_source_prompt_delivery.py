"""Actual provider presentation with constructed inputs and scripted choices."""
import asyncio
from copy import deepcopy

from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_ratio_source_prompt import SOURCE_RATIO_TASK
from gene_annotation_episode.literature_ratio_source_render import _safe_definition, hidden_records
from literature_ratio_source_worker_fixture_077 import make_case, run_case


def test_actual_jats_percentage_retains_variant_inside_expression_and_full_tasks(tmp_path):
    store,case=make_case(tmp_path/'state')
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run',mode='jats'))
        parent=provider.presented[-1];steering=parent.split('\n\nSTEERING\n',1)[1]
        assert 'K426A' in steering and '64%' not in steering and '0.64' in steering
        assert '1–253' in steering and '37 °C' in steering and 'pH 7.4' in steering
        texts=[text for state,text in zip(provider.contexts,provider.presented) if 'literature_assignment' in state]
        assert len(texts)==3 and all(text.count(SOURCE_RATIO_TASK)==1 for text in texts)
        tasks=[text.split('\n\nSTEERING\n',1)[0] for text in texts]
        assert tasks[0]==tasks[1]
        # The same-decision contract lookup appends the exact requested
        # operation contract while retaining the full recurring assignment.
        assert tasks[1] in tasks[2]
        assert 'Complete requested contract' in texts[2]
    finally:store.close()


def test_actual_broad_source_label_withheld_without_changing_known_status(tmp_path):
    store,case=make_case(tmp_path/'state')
    try:
        _,provider,_=asyncio.run(run_case(store,case,tmp_path/'run',broad_label=True))
        state=provider.contexts[-1];row=state['child_reports'][0]['requested_signal'][0]
        assert row['meaning_statuses']['condition']=='known'
        text=provider.presented[-1].split('\n\nSTEERING\n',1)[1]
        assert '128.000' not in text and '200.000' not in text
        assert '| condition | known | source-bound definition retained for scoped access |' in text
        assert 'K426A' in text and '1–253' in text
    finally:store.close()


def test_all_numeric_candidate_regions_and_frame_identity_filter_display():
    witness={'authentication':'native_view_bytes_and_geometry','locator':{
        'kind':'image','original_artifact_ref':'artifact_engineering','frame':1,'region':[5,5,15,15]}}
    loci=[{'kind':'image','original_artifact_ref':'artifact_engineering','frame':1,'region':[100,100,120,120]},
          {'kind':'image','original_artifact_ref':'artifact_engineering','frame':1,'region':[10,10,20,20]}]
    # First candidate alone is disjoint; the alternative candidate overlaps.
    assert not _safe_definition('K426A',witness,loci,set())
    changed=deepcopy(witness);changed['locator']['frame']=0
    assert _safe_definition('K426A',changed,loci,set())
    changed=deepcopy(witness);changed['locator']['region']=[30,30,50,50]
    assert _safe_definition('37 °C; pH 7.4',changed,loci,set())


def test_generic_expansion_hides_source_ratio_refs_and_keeps_unrelated_facts():
    row={'candidate_basis':'selected_received_source_representations',
        'uncertainty_evaluation':'numeric_uncertainty_reader_unimplemented',
        'evidence_source_ref':'source_engineering','sheet_ref':'source_private_sheet',
        'input_measurement_refs':['reference_private']}
    records={'reference_private':{'source_ref':'source_engineering','label':'128.000'},
        'reference_broad':{'source_ref':'source_engineering','label':'128.000 / 200.000'},
        'reference_unrelated':{'source_ref':'source_other','label':'Independent received fact'}}
    hidden=hidden_records([{'arbitrary_name':[row]}],records)
    assert {'source_private_sheet','reference_private','reference_broad'}<=hidden
    assert 'reference_unrelated' not in hidden


def test_multiple_jats_paragraphs_withhold_ambiguous_display_without_digit_rule():
    witness={'authentication':'exact_utf8_span','locator':{'kind':'text_span',
        'source_ref':'source_constructed','artifact_ref':'artifact_constructed',
        'representation':'original','start':10,'end':22,'quote':'64% (K426A)'}}
    first={'kind':'jats','artifact_ref':'artifact_constructed','paragraph_text':'64% (K426A)',
        'numeric_start':0,'numeric_end':3}
    second={'kind':'jats','artifact_ref':'artifact_constructed','paragraph_text':'80% (another form)',
        'numeric_start':0,'numeric_end':3}
    assert _safe_definition('K426A',witness,[first],{'64%'})
    # Exact008 lacks an original-byte/paragraph mapping for the other paragraph.
    # Conservative display withholding is explicit; the caller's known status
    # is unchanged. No claim of universal essential-label display is made.
    assert not _safe_definition('K426A',witness,[first,second],{'64%','80%'})
