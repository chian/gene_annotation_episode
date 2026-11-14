"""Credit for the original commissioned literature answer and saved scientific evidence."""
from dataclasses import dataclass, replace
import json
import math
from gene_annotation_episode.domain import ContractError, identity
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .commission_contract import commissioned_task, continuation_task
from gene_annotation_episode.episodic_workflow.root.library.literature_task_schema import VERSION
from .task_answers import lead_dispositions, screening_answers, _current_assessments

@dataclass(frozen=True)
class LiteratureTaskCredit:
    binding: object
    context: object
    requires_episode_receipts = True
    requires_known_record_refs = True
    requires_receiver_context = True

    def as_record(self):
        task, _ = commissioned_task(self.context)
        return {'kind': VERSION, 'task': continuation_task(self.context),
            'credit_unit': task['credit_unit'], 'unit': (
                'one_current_graded_assessment_per_original_experiment' if task['kind'] == 'a105_experiments'
                else 'one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads'
                else 'one_answer_to_original_commission'),
            'revision_credit': False, 'activity_credit': False,
            'annotation_support': 'separate'}

    def __call__(self, store, scope, *, known_record_refs, assignment, episode_id, run_id):
        task, proposed = commissioned_task(self.context)
        request = plain(self.context.request)
        expected = {'goal': request['goal'], 'scope': plain(self.context.scope),
            'purpose': request['report_contract']['decision'],
            'schema': request['report_contract']['measurements']['schema'],
            'initial_report': request['message']['initial_report']}
        if (run_id != self.context.run_id or episode_id != self.context.episode_id
                or store.validate_scope(scope) != store.validate_scope(plain(self.context.scope))
                or any(plain(assignment).get(key) != value for key, value in expected.items())
                or assignment.get('proposed_annotation_ref', proposed) != proposed):
            raise ContractError('literature_task_credit_commission_mismatch')
        hypothesis = store._require(proposed, {'hypothesis'})
        if not store.reference_subset([proposed], plain(scope)):
            raise ContractError('literature_task_annotation_outside_scope')
        if not set(store._record_roots('hypothesis', hypothesis)).intersection(scope['subject_refs']):
            raise ContractError('literature_task_requires_target_annotation')
        known = set(known_record_refs)
        context = replace(self.context, received_record_refs=tuple(known))
        with store.read_snapshot():
            items, unresolved = self._answers(store, context, task, proposed, known)
        credit = task['credit_unit'] * len(items)
        if not math.isfinite(credit):
            raise ContractError('literature_finite_task_credit_required')
        return {'credit': credit, 'scope': plain(scope),
            'proposed_annotation_ref': proposed, 'policy': self.as_record(),
            'task_status': 'unresolved_contract' if unresolved else 'answered' if items else 'unanswered',
            'unresolved': unresolved, 'source_contributions': items,
            'commission_ref': identity('literature_task_commission', self.context.as_record())}

    def _answers(self, store, context, task, proposed, known):
        kind, answer = task['kind'], task.get('answer_kind')
        if kind == 'verified_source_leads':
            return [lead for lead in lead_dispositions(store, context) if lead['disposition'] == 'relevant'], []
        if answer == 'screening':
            return screening_answers(store, context), []
        if answer == 'assessment':
            for record in _current_assessments(store, context, proposed, known):
                observation = store.get(record['observation_ref'])
                if observation['source_ref'] in task['source_refs'] and (
                        observation.get('anchor') is not None or observation.get('visual_anchor') is not None):
                    return [{'assessment_ref': record['id'], 'source_ref': observation['source_ref']}], []
            return [], []
        if answer == 'measurement':
            return self._measurement(store, context, task, known), []
        from gene_annotation_episode.episodic_workflow.root.literature_sheet_updates import current_sheet_refs
        if kind == 'a105_experiments':
            from gene_annotation_episode.episodic_workflow.root.literature_assay_grading_storage import LiteratureAssayGradingRepository
            from gene_annotation_episode.episodic_workflow.root.literature_required_grading import _matches_grading
            repository = LiteratureAssayGradingRepository(store, context.run_id)
            assessments = list(_current_assessments(store, context, proposed, known))
            wanted = {item['experiment_ref']: item['assay_type'] for item in task['experiments']}
            completed = {}
            for ref in current_sheet_refs(store, context, repository.provider):
                if ref not in known:
                    continue
                saved = repository.read(ref)
                args = saved['selection']
                experiment = args.get('experiment_ref')
                if args['assertion_ref'] != proposed or wanted.get(experiment) != args['assay_type']:
                    continue
                # Owning a source handle alone does not grant another child's grade.
                if not repository.fact_cells(context, [ref], components=repository.components):
                    continue
                for assessment in assessments:
                    if _matches_grading(store, assessment['id'], args, contextual=False):
                        completed[experiment] = {'experiment_ref': experiment,
                            'assessment_ref': assessment['id'], 'sheet_ref': ref}
            return list(completed.values()), []
        from gene_annotation_episode.episodic_workflow.root.literature_a105_aggregation_storage import LiteratureA105AggregationRepository
        repository = LiteratureA105AggregationRepository(store, context.run_id)
        current_grades = set(current_sheet_refs(store, context, 'literature.a105.assay_grading'))
        for ref in current_sheet_refs(store, context, repository.provider):
            if ref not in known:
                continue
            saved = repository.read(ref)
            args = saved['selection']
            if (args['assertion_ref'] != proposed or set(task['experiment_refs']) != {
                    item['experiment_ref'] for item in args['experiments']}):
                continue
            # Automatic discovery creates an unbound scaffold. Assembly needs
            # selected current inputs; a selected grader may explicitly report
            # an unavailable value, but an unselected input is not an answer.
            selected = [experiment['metrics'][metric] for experiment in args['experiments']
                for metric in task['metrics']]
            if any(item is None or item['sheet_ref'] not in current_grades for item in selected):
                continue
            cells = repository.fact_cells(context, [ref], components=task['metrics'])
            if {row['component'] for row in cells} == set(task['metrics']):
                return [{'sheet_ref': ref, 'experiment_refs': task['experiment_refs'],
                    'metrics': task['metrics']}], []
        return [], []

    def _measurement(self, store, context, task, known):
        repository = self.binding.services.literature_quantity_repository()
        for ref in known:
            source = store.get(ref)
            if source.get('provider') != repository.provider:
                continue
            request = json.loads(store.get_artifact(source['request_ref']))
            if request.get('arguments') != task['selection']:
                continue
            repository.read(ref)
            rows = repository.fact_cells(context, [ref], components=task['components'])
            if {row['component'] for row in rows} != set(task['components']):
                continue
            # This reader preserves an unreported spread as an explicit unknown.
            if all(row['status'] == 'populated' or row.get('unavailable_reason') in {
                    'reported_spread_unavailable', 'zero_reported_value'} for row in rows):
                return [{'sheet_ref': ref, 'source_ref': task['selection']['source_ref'],
                    'components': task['components']}]
        return []
