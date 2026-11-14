"""Original exact literature fact boundary and finite rejection regressions."""
from copy import deepcopy

import pytest

from ..communication import ReportBoundaryError, validate_closed_schema, validate_form
from ..domain import obj
from ..literature_task_credit import LEADS, SCREENING, lead_return_schema, screening_schema
from .source_family_checks import fixture


def test_only_exact_native_lead_and_screening_return_schemas_are_admitted():
    from gene_annotation_episode.episodic_workflow.root.a102.communication import ReportBoundaryError, validate_closed_schema
    for factory in (lead_return_schema, screening_schema):
        validate_closed_schema(obj({'answer': factory()}))
        altered = factory()
        altered['items']['properties']['unverified_free_text'] = {'type': 'string'}
        with pytest.raises(ReportBoundaryError, match='must match its registered source'):
            validate_closed_schema(obj({'answer': altered}))


@pytest.mark.parametrize('factory', [lead_return_schema, screening_schema], ids=['leads', 'screening'])
@pytest.mark.parametrize('mutation', ['source', 'object_depth', 'array_depth', 'namespace'])
def test_original_fact_source_identity_depth_and_reference_schema(factory, mutation):
    field = factory()
    if mutation == 'source':
        field['x-source'] = SCREENING if field['x-source'] == LEADS else LEADS
        schema = obj({'answer': field})
    elif mutation == 'object_depth':
        schema = obj({'nested': obj({'answer': field})})
    elif mutation == 'array_depth':
        schema = obj({'nested': {'type': 'array', 'items': field}})
    else:
        field['items']['properties']['proposed_annotation_ref']['x-reference-namespace'] = 'source'
        schema = obj({'answer': field})
    with pytest.raises(ReportBoundaryError) as failure:
        validate_closed_schema(schema)
    assert failure.value.diagnostic['code'] == 'invalid_schema'


@pytest.mark.parametrize('task_kind', ['verified_source_leads', 'screening'])
def test_original_payload_reference_and_saved_work_guards(tmp_path, task_kind):
    with fixture('published_evidence_assessment', tmp_path / 'actual', task_kind) as v:
        schema = deepcopy(v.schema)
        resolve = lambda reference, namespace: v.binding.resolve(v.context, reference, namespace)
        assert validate_form({'answers': []}, schema, resolve) == {'answers': []}
        assert v.binding.validate_received_report(v.context, {'answers': []}, schema) is None
        if task_kind == 'verified_source_leads':
            from dataclasses import replace
            commit = {key: [] for key in v.store.reasoning_schema()['properties']}
            anchor = {'source_ref': v.source['id'], 'artifact_ref': v.artifact,
                'start': 0, 'end': len(v.raw), 'quote': v.raw.decode()}
            commit['source_subjects'] = [{'alias': 'construct', 'reference_type': 'construct',
                'source_ref': v.source['id'], 'label': 'Original synthetic source',
                'anchor': anchor}]
            committed = v.store.commit_reasoning(commit, v.store.validate_scope(), 'boundary-source-subject')
            assert committed['status'] in ('completed', 'partial'), committed
            subject = committed['aliases']['construct']
            v.workflow.receipts.receive(v.context.episode_id, committed['record_refs'], kind='initial')
            v.context = replace(v.context,
                received_record_refs=tuple(v.workflow.receipts.known(v.context.episode_id)))
            record = v.store.get(subject)
            assert record['record_type'] == 'reference' and record['source_ref'] == v.source['id']
            assert record['anchor'] == anchor
            assert not resolve(v.store.problem()['subject_refs'][0], 'reference')
            row = {'proposed_annotation_ref': v.proposed, 'source_ref': v.source['id'],
                'subject_ref': subject, 'disposition': 'relevant',
                'relevance_rationale': 'Synthetic boundary input; no saved source judgment or biological support.',
                'witness': {'source_ref': v.source['id'], 'representation': 'original',
                    'start': 0, 'end': len(v.raw), 'quote': v.raw.decode()}}
        else:
            row = {'proposed_annotation_ref': v.proposed, 'disposition': 'no_applicable_evidence',
                'examined': [{'source_ref': v.source['id'], 'artifact_ref': v.artifact,
                    'start': 0, 'end': len(v.raw)}], 'annotation_support': 'not_assessed'}
        form = {'answers': [row]}
        original = deepcopy(form)
        # Shape/reference validity is separate from saved scientific authority.
        assert validate_form(form, schema, resolve) == original
        with pytest.raises(ReportBoundaryError, match='reference is unavailable'):
            validate_form(form, schema, lambda reference, namespace:
                reference != v.proposed and resolve(reference, namespace))
        with pytest.raises(ReportBoundaryError) as unsaved:
            v.binding.validate_received_report(v.context, form, schema)
        assert unsaved.value.diagnostic['code'] == 'literature_task_answer_differs_from_saved'
        malformed = deepcopy(form)
        malformed['answers'][0]['unrecorded_field'] = 'not admitted'
        with pytest.raises(ReportBoundaryError) as payload:
            validate_form(malformed, schema, resolve)
        assert payload.value.diagnostic['code'] == 'additionalProperties'
        assert form == original and schema == v.schema
