"""The A106 leaf extraction: the perturbation sheet's form filled once from one item a leaf episode reads (a chunk, a table
region, a window of a document read in order). The leaf episodes (``passage_evidence_extraction``,
``table_evidence_extraction``, ``source_coverage_improvement``) each call these functions from their own ``task.py``,
``credit.py`` and ``messages/internal_summary.py`` with their own pieces: what the text is called (``text``: 'chunk', 'table',
'window'; the noun of the instructions and the context key of the text), an optional sentence of their own on how their text
reads (``reading``), their role and their goal.

The axis's own extraction form is the perturbation population (``literature.perturbation.populate``, schema
``perturbation_population_schema``): the molecule, recipient, donor, experiment, arms, endpoint, condition and intended change
as source quotations, the design and measurement interpretations as a fixed vocabulary, the interpretation witnesses and the
reported arm summaries (``source_measurements``). What the model fills is that form without what code sets (the source, the
source kind, the retained-data reference) and without the assessment of an experiment (a leaf holds no experiment record to
assess), and with every source witness as a quotation only. ``extraction_call`` finds each quotation in the item (it must
occur exactly once; otherwise the answer is rejected before any unit exists and ``decide`` asks again with the reason), turns it
into the witness the population route reads (the source, the page's representation and the byte interval) and checks the
whole against the population schema. The unit, ``extract`` (``perturbation_extraction``), then saves the sheet through the
population route over the custody-scoped store: the route authenticates every quotation against the source bytes, reads the
numbers from them (the model never types one) and computes the sheet's cells. A route refusal is the unit's ``invalid`` outcome;
it enters the iterator like any returned outcome."""
from copy import deepcopy
from functools import lru_cache

from jsonschema import ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.perturbation_evidence.literature_perturbation_inputs import (
    perturbation_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage import literature_population_route as route
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    obj, source_location_inputs, validate_schema)

OPERATION = 'literature.perturbation.populate'
SOURCE_KIND = 'primary_source'      # a leaf reads a published source
REPRESENTATIONS = ('text', 'original')      # the representations a witness can name
SET_BY_CODE = ('source_ref', 'source_kind', 'data_source_ref', 'experiment_assessment')
WITNESS_FIELDS = {'source_ref', 'representation', 'start', 'end'}

INSTRUCTIONS = (
    'You are one step of a system that scores how well published perturbation experiments (a deletion, a replacement, a '
    'truncation, a reconstitution, each with its restoration) support a proposed annotation of a molecule. You are given one '
    '{text} of text from a published source. Fill the form with what the {text} itself reports about one perturbation '
    'experiment and nothing else: the molecule, the recipient, the donor, the experiment, the reference, perturbed and '
    'restored arms, the endpoint, the normalization, the condition and the intended change are each a quotation from the '
    '{text} or null when the {text} does not state it; the design, the measurement status, the endpoint scope and the amount '
    'role are values of a fixed vocabulary, unknown when the {text} does not settle them, and each interpretation that is not '
    'unknown needs a quotation among the interpretation witnesses. Give the reported arm summaries in source_measurements '
    'as quotations of the printed numbers and their units (a number is read by the host from the quotation, never typed '
    'by you); an arm the {text} does not report stays null. A quotation is a span of the {text} exactly as written and must '
    'occur in the {text} exactly once: when a value alone occurs more than once, extend the quotation until it occurs once. '
    'Extract exactly what the form asks and nothing else; a field the {text} does not state stays null or unknown. '
    'The host checks every quotation, finds its place in the source and computes the sheet; you grade nothing and do '
    'not decide anything else.')


def extraction_instructions(text, reading=''):
    """The instructions of one extraction of a ``text`` (the noun) that reads as ``reading`` says."""
    return INSTRUCTIONS.format(text=text) + reading


def quotation_only(schema):
    """``schema`` with every source witness (the object with the source, representation and byte interval of a quotation,
    once the library has projected away the quote) replaced by the quotation alone."""
    if isinstance(schema, list):
        return [quotation_only(value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    result = {key: quotation_only(value) for key, value in schema.items()}
    properties = result.get('properties')
    if isinstance(properties, dict) and WITNESS_FIELDS <= set(properties) <= WITNESS_FIELDS | {'kind'}:
        fields = {key: properties[key] for key in properties if key == 'kind'}
        fields['quote'] = {'type': 'string', 'minLength': 1,
                           'description': 'A span of the text exactly as written; it occurs in the text exactly once.'}
        return obj(fields)
    return result


@lru_cache(maxsize=None)
def population_schema():
    """The closed schema the population route admits (source locations as inputs, no quote)."""
    return source_location_inputs(perturbation_population_schema())


@lru_cache(maxsize=None)
def answer_schema():
    """The form the model fills: the population form without what code sets, source_measurements asked for, every witness a
    quotation."""
    schema = deepcopy(population_schema())
    for name in SET_BY_CODE:
        schema['properties'].pop(name, None)
    schema['required'] = [name for name in schema['properties']]
    return quotation_only(schema)


def located(value, data, offset, source_ref, representation):
    """``value`` (an answer) with each quotation replaced by the witness of its place: ``data`` are the bytes of the item,
    ``offset`` is the byte offset of the item in the artifact of the page's ``representation``. A quotation that does not
    occur in the item exactly once is a ``ValueError``."""
    if isinstance(value, list):
        return [located(item, data, offset, source_ref, representation) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value) <= {'kind', 'quote'} and 'quote' in value:
        quote = value['quote'].encode('utf-8')
        if data.count(quote) != 1:
            raise ValueError('quote_not_found_exactly_once:' + str(data.count(quote)))
        start = offset + data.index(quote)
        return {**{key: value[key] for key in value if key == 'kind'}, 'source_ref': source_ref,
                'representation': representation, 'start': start, 'end': start + len(quote)}
    return {key: located(child, data, offset, source_ref, representation) for key, child in value.items()}


def extraction_request(content, feedback, *, text, reading=''):
    """The model request of one extraction of ``content`` (the text the episode reads, shown in the context under the key
    ``text``); ``feedback`` is why the previous answer was rejected (None at first)."""
    context = {text: content, 'previous_answer_was_rejected_because': feedback}
    return ModelRequest('REASONING', extraction_instructions(text, reading), context,
                        generation_schema(deepcopy(answer_schema())))


def extraction_call(response, content, *, page, offset, scope, assignment, proposed_annotation_ref):
    """The ``extract`` call of the model's ``response`` to an extraction of ``content`` (the item that starts at byte
    ``offset`` of the page's artifact): the quotations are found in the item and the answer is checked against the population
    schema; a refused answer raises ``Rejected`` with the reason, before any unit exists. The call's arguments are the
    envelope the population route reads."""
    try:
        answer = decode_response(response, answer_schema())
        validate_schema(answer, answer_schema())
        arguments = {'source_ref': page['source_ref'], 'source_kind': SOURCE_KIND, 'data_source_ref': None,
                     **located(answer, content.encode('utf-8'), offset, page['source_ref'], page['representation'])}
        validate_schema(arguments, population_schema())
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall('extract', {'arguments': arguments, 'scope': scope, 'page_source_ref': page['source_ref'],
                                'assignment': assignment, 'proposed_annotation_ref': proposed_annotation_ref})


def perturbation_extraction(envelope, ctx, role, goal):
    """The unit: save the perturbation sheet the answer makes, through the population route over the unit's custody-scoped
    store. Returns the route's outcome (``completed`` with the sheet's reference, or ``invalid`` with its reason)."""
    return route.populate(OPERATION, envelope, ctx, role, goal)


def window_text(records, page, offset, limit):
    """The text of the item: the bytes ``[offset, offset + limit)`` of the artifact of the page's representation, read
    through the custody reader ``records``."""
    return records.get_artifact(page['artifact_ref'])[offset:offset + limit].decode('utf-8')


def saved_sheet_refs(outcomes):
    """The sheets the completed ``extract`` units saved, in order."""
    return [outcome['outcome']['result']['sheet_ref'] for outcome in outcomes
            if outcome['kind'] == 'tool' and outcome['tool'] == 'extract' and outcome['outcome']['status'] == 'completed']
