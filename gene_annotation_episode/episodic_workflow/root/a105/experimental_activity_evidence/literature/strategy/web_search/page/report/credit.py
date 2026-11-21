"""Credit: the commissioned literature task's credit, ``credit_unit`` for each answer to the original commission
(the old ``credit.py``: ``credit_kind`` 'scientific', ``credit_projector`` ``LiteratureTaskCredit``), computed by the
library's ``literature_task_answers.classified_task_credit`` over this episode's summary and held records. Per task
kind the answers are: the relevant source leads (``verified_source_leads``); the screening of every commissioned span
(``screening``); one current anchored retained assessment (``assessment``); a populated quantity sheet of the
commissioned selection (``measurement``); one aggregation sheet over the commissioned experiments
(``a105_assembly``); and for ``a105_experiments`` the current grading sheet of each commissioned experiment, matched
to a current assessment, which earns the share of the unit its fields earn.

The credit of a grading sheet rests on the classification of the fields it leaves unknown, not on the sheet existing
(owner, 19 November 2026; AGENTS.md "Required literature evidence processing"). A field the grading entered earns its
share. A field it left unknown (a null quantity, a null prediction model, a criterion ``unknown``) earns its share
when the classification holds it justified (the source windows the Episode read do not state it: the partial or
unresolved grading a missing measurement requires) and nothing when it holds it unjustified (those windows state it:
the grading missed it) or when no classification is held. A sheet of nothing but unjustified unknowns earns nothing.
Never bounded, clamped or rescaled.

``classify_unknowns`` makes that classification. It is credit assignment and is automatic: the unit that saves a
sheet (``task.py`` ``reason``) calls it as its tail, the model never selects it and no tool offers it. It is one typed
model call per sheet through ``ctx.model`` (recorded with the unit and replayed), answered in a closed schema (one of
``justified`` / ``unjustified`` per unknown field, validated by code) and saved as a record the Episode holds.
``credit`` stays a pure read of the summary and the held records."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_task_answers import (
    classified_task_credit)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_unknown_classification import (
    classification_record, classification_request, classification_result, unknown_fields, window_texts)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical)


async def classify_unknowns(outcome, scope, windows, ctx):
    """The tail of a grading unit: classify the unknown fields of each sheet the unit saved against ``windows`` (the
    spans of the source this Episode read) and save each result as a held record. ``outcome`` is the unit's outcome;
    it is returned with ``unknown_classifications`` (per sheet: the sheet, the saved record, the status of each
    unknown field). A sheet that leaves no field unknown has nothing to classify, and without a read window there is
    nothing to classify against: its unknown fields stay unclassified and earn nothing."""
    processing = outcome.get('evidence_processing')
    if processing is None or processing['kind'] != 'graded':
        return outcome
    texts, repository, classified = window_texts(ctx.store, windows), LiteratureAssayGradingRepository(ctx.store), []
    for grading in processing['gradings']:
        sheet_ref = grading['result']['sheet_ref']
        selection = repository.read(sheet_ref)['selection']
        if not unknown_fields(selection) or not texts:
            continue
        request = classification_request(sheet_ref, selection, texts)
        answer = await ctx.model.complete('REASONING', request['instructions'], request['context'],
                                          generation_schema(request['output_schema']))
        result = classification_result(sheet_ref, selection, decode_response(answer, request['output_schema']))
        record = ctx.store.put('source', classification_record(ctx.store.artifact(canonical(result),
                                                                                  'application/json')),
                               origin='tool', scope=scope)
        classified.append({'sheet_ref': sheet_ref, 'classification_ref': record['id'], 'fields': result['fields']})
    return {**outcome, 'unknown_classifications': classified}


def credit(summary, records):
    return classified_task_credit(summary, records)
