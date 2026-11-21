"""The task: one model-selected action per unit, over the pinned A104 selection of this episode.

Carried from the old ``task.py`` / ``task_state.py`` / ``task_instructions.py`` / ``action_admission.py`` /
``action_execution.py`` / ``decision_context.py`` / ``decision_inputs.py`` / ``presentation*.py`` /
``tool_selection.py`` / ``scientific_operations.py`` / ``child_commissioning.py`` / ``goal.py`` (the instruction
text). One unit is one action the model selects: a tool (the selected actual tools of the pinned selection, the
``process.search/entry/sources`` and ``knowledge.search/entry/read`` lookups, ``process.revise``), the committed
scientific interpretation (``reason``), one A104 phylogeny tool (the old ``a104_tools.py`` at ``60889621e``:
``phylogeny.inspect`` and the four measurement operations that each publish one native sheet and its per-use
attribution, plus the judged historical-cause cell) or the commission of a child (``episode_child``). The task always
offers a unit and never ends the Episode: only the yield controller does. The old ``wait`` (never permitted here) and
``redeliver_report`` actions, the decision exchange and the saved state are not carried. There is no prose ``report``
tool: what the parent receives is the credit and the controlled features code reads from the saved A104 sheets
(``messages/final_to_parent.py``).

Offered children: the old ``allowed_child_roles`` kept ``evolutionary_history_evidence`` (this episode again, a
narrower investigation) and ``hpc`` (``hpc_work_planning``); the slots ``launch``, ``monitor``, ``results`` and
``literature`` are declared (the old request assemblers existed for them, see ``messages/msg_to_child.py``) but, as
in the old code, are not offered to the model.

Settings this episode reads (``ctx.settings``): ``process_library_directory`` (the frozen process library),
``tool_library_directory`` (the frozen scientific tool library), ``tool_registry`` (the keyword settings of the
A104 ``ToolRegistry``), and the optional library directories ``tool_knowledge_directory`` and
``launch_instruction_directory``; ``yield_bindings`` is read by ``yield_estimator.py``.

Not placed (no module in ``episode_support/`` today; the old modules lived in the old shared root): the common tools
``process.tools`` (``scientific_tool_retrieval``), ``process.execution`` (``execution_planning.catalog`` and
``read``), ``episode.credit``, ``episode.annotation_score``, ``episode.monitoring_information``,
``episode.estimate_wait`` and the five ``shared.*`` information tools. They are not offered to the model.
``episode.history`` is the unit index and the last outcome of the summary; ``episode.credit`` is the credit view of
the summary."""
import inspect
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.schema_support import _schema_nodes

from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.attribution import (
    refresh as refresh_attribution)
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.history_explanation import (
    GRADING_INSTRUCTIONS as EXPLANATION_INSTRUCTIONS, LEVELS as EXPLANATION_LEVELS, publish_explanation)
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.native_publications import (
    native_observation, publish as publish_measurement, received_measurement)
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.scoring import (
    clade_composition, compare_placements, history_comparison, placement, relationship_inventory)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc import (
    native_body, require)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence.evidence_axis_instructions import (
    VERSION as INSTRUCTION_VERSION, instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence.runtime_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.evolutionary_history_evidence.process_options import (
    EvolutionaryHistoryEvidenceLibrary, catalog as process_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.construction_records import (
    CHILD_SELECTION_VERSION, REVISION_ORIGIN_VERSION, SELECTION_VERSION, scientific_digest, scientific_invocation_ref,
    selection_fields, validate_child_selection, validate_revision_origin, validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    identity, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.evolutionary_history_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import GOAL

_PREFIX = 'evolutionary_history_evidence/'
CHILD_SLOTS = {'evolutionary_history_evidence': 'evolutionary_history_evidence',
               'hpc': _PREFIX + 'hpc_work_planning',
               'launch': _PREFIX + 'execution_job_submission',
               'monitor': _PREFIX + 'execution_progress_assessment',
               'results': _PREFIX + 'execution_result_acquisition',
               'literature': _PREFIX + 'published_evidence_assessment'}
SERVICES = ()
MODEL_ROLE = 'REASONING'
# How the action schema travels to the model: the model endpoint takes no open object, so a record whose fields the
# schema leaves open (a child's ``scope`` and ``initial_report``) travels as JSON text and is decoded here.
TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'a104_tool_argument_transport_unsupported'}
# The old ``allowed_child_roles``: the children the model is offered.
OFFERED_CHILDREN = ('evolutionary_history_evidence', 'hpc')
# The old ``_COMMON_TOOLS`` (a selected tool may not reuse one of these names or ``process.revise``).
COMMON_TOOL_NAMES = ('process.search', 'process.entry', 'process.sources', 'process.tools', 'knowledge.search',
                     'knowledge.entry', 'knowledge.read', 'episode.history', 'episode.credit',
                     'episode.annotation_score', 'episode.monitoring_information', 'episode.estimate_wait',
                     'shared.request_information', 'shared.publish_information',
                     'shared.resolve_information_need', 'shared.read_information', 'shared.list_information')
PROCESS_LOOKUPS = ('process.search', 'process.entry', 'process.sources')
KNOWLEDGE_LOOKUPS = ('knowledge.search', 'knowledge.entry', 'knowledge.read')
# The old ``scientific_operations.execute``: the received records are the permitted refs of these two tools.
PERMITTED_RECORD_TOOLS = ('result.blast.hsp', 'source.locate')
# The return fields (selectable fields of each child's own return form) this task offers the model to select.
RETURN_FIELDS = {
    'evolutionary_history_evidence': ('committed_record_refs',),
    'hpc': ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs')}
CHILD_PURPOSE = {
    'evolutionary_history_evidence':
        'Commission a narrower evolutionary-history investigation of this evidence axis with its own thought '
        'pattern and selected tools (copy result.selection and revision_origin of process.revise into its '
        'assignment). It returns its own credit and finding, always the records its interpretations committed, and '
        'the facts you select.',
    'hpc':
        'Commission HPC work planning for a configured commission or a scientific tool computation to implement '
        'through the HPC template: it owns the commission ledger, plans, launches, monitors and collects real work '
        'and returns its own credit and finding and the facts you select.'}
REVISION_DESCRIPTION = (
    'Prepare a different thought pattern and/or selected actual tools for a new child investigating the same '
    "evidence axis. Return its selection for a separately selected episode_child commission with the child's job, "
    'scope, constraints and typed return form. Copy result.selection and revision_origin into that assignment. '
    'Changes no current process, starts no child and records no biological observation. Select the actual '
    'tool/resource choices returned by process.tools for the desired investigation.')
_SHA256 = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
_TEXT = {'type': 'string', 'minLength': 1}
RETURN_GUIDANCE = (
    '\nWhat returns to your parent is your credit and the features code reads from the A104 sheets you saved with the '
    'phylogeny tools (per native measurement: its evidence type, support, sizes, distances, agreement, attribution '
    'bounds and the judged historical cause; per target: the attributed dimensions and lengths); no prose of yours is '
    'returned. Nothing but the configured controller ends this episode.')

# The A104 phylogeny tools (the old ``a104_tools.NAMES`` and ``catalog`` descriptions, the owner's text): python tool
# name -> (the library's tool name, description). Each measurement operation publishes one native sheet (placement,
# history comparison, clade composition, robustness) and then the per-use attribution of every held measurement.
_REF = {'type': 'string', 'format': 'reference'}
PHYLOGENY_TOOLS = {
    'phylogeny_inspect': ('phylogeny.inspect',
        'Read actual received native tree splits, their support, original tip/region/taxon bindings, '
        'and available independent organismal analyses. corresponding_relationships matches physical '
        'reference groups across analyses and supplies their analysis-local split indices. '
        'This is a read, with no new scientific score.', obj({'native_ref': _REF})),
    'phylogeny_measure_placement': ('phylogeny.measure_placement',
        'Measure one actual native target-containing split and its original bootstrap population. '
        'Return its exact target region and reference members. Function and biological rooting remain separate.',
        obj({'native_ref': _REF, 'analysis': _TEXT, 'split_index': {'type': 'integer', 'minimum': 0}})),
    'phylogeny_compare_histories': ('phylogeny.compare_histories',
        'Calculate shared-tip unrooted relationships between the actual family and independent '
        'organismal tree. Supply one explicit copy per taxon and include the target. Retain omitted taxa and '
        'native support. Discordance alone does not diagnose transfer.',
        obj({'native_ref': _REF, 'family_analysis': _TEXT, 'organismal_analysis': _TEXT,
             'tip_ids': {'type': 'array', 'items': _TEXT, 'uniqueItems': True, 'minItems': 4}})),
    'phylogeny_clade_functions': ('phylogeny.clade_functions',
        'Measure characterized and unknown membership of this particular native clade using received '
        'A105 experimental worksheet links. Copied protein names cannot characterize members. Missing '
        'reference characterization is published to the shared parent; it does not erase other native tests. '
        'Supply the measurement_ref returned by phylogeny.measure_placement as placement_ref.',
        obj({'placement_ref': _REF})),
    'phylogeny_compare_placements': ('phylogeny.compare_placements',
        'Compare genuinely different native placement analyses over the same target region and '
        'declared reference-member set. Retain conflicting placements as a compared set rather than picking '
        'the highest support. Supply the measurement_ref values returned by phylogeny.measure_placement.',
        obj({'placement_refs': {'type': 'array', 'items': _REF, 'uniqueItems': True, 'minItems': 2}})),
    'phylogeny_explain_history': ('phylogeny.explain_history',
        'Grade a horizontal-transfer explanation of an actual outlying placement on its own ordinal sheet '
        '(contradicted, plausible_only, corroborated or unknown), separate from tree support and never a weight on '
        'it. Supply the measurement_ref of the native placement or history comparison it explains and the held '
        'records that bear on the grade.',
        obj({'measurement_ref': _REF, 'grade': {'enum': list(EXPLANATION_LEVELS)},
             'support_refs': {'type': 'array', 'items': _REF, 'uniqueItems': True}})),
}
PHYLOGENY_NAMES = {library: name for name, (library, _, _) in PHYLOGENY_TOOLS.items()}


def phylogeny_entries():
    """The A104 phylogeny tools as the model is shown them (name, description, input schema)."""
    return [{'name': library, 'description': description, 'input_schema': schema}
            for library, description, schema in PHYLOGENY_TOOLS.values()]



# The owner's grading instructions: what each A104 sheet keeps apart (``scoring.py``, ``attribution.py``,
# ``characterization.py``) and the historical-cause rubric; part of the instructions of every decision.
GRADING_SECTION = (
    '\nA104 sheets (phylogeny tools). Native numerical support is never a function probability; input identity, '
    'experimental characterization and evolutionary interpretation remain separate. Each measurement publishes a '
    'native sheet that attributes its value to this one tree test and original target region and keeps function '
    'interpretation separate; numerical arguments cannot be supplied through a model assessment: the producer '
    'recalculates every sheet from the exact native operands. A104 grades exactly four native measurement kinds, '
    'each on the unit interval (placement, history comparison, clade composition, robustness); an unevaluable value '
    'stays unknown, never 0. Bootstrap percent and bootstrap fraction are one statistic; posterior and bootstrap '
    'support are never averaged. Each tool use then gets a per-use attribution sheet (score, raw value, bounds, '
    'attributed or unresolved state, missing inputs, variant group: the same test repeated is one variant group) '
    'with target identity, execution, native test, functional scope and historical cause kept as separate '
    'sub-sheets, never an aggregate or a multiplier of A101 or A105. A clade test counts a member as characterized '
    'only when a received A105 assay-grading sheet has every common criterion and every criterion of its assay type '
    'supported, from a single-subject assay; a whole-protein assay cannot identify a selected subregion\'s activity; '
    'an assayed construct maps to a panel member only through identical amino-acid sequence; the clade score is '
    'scaled by the native MSA identity and matched extent of each characterized reference, and uncharacterized '
    'members widen the bounds. A robustness test needs genuinely different analyses over the same target region and '
    'declared member scope; distinct compatible branches are not replicates; conflicting placements are retained.\n'
    + EXPLANATION_INSTRUCTIONS + '\n')



def _ref_schema(slot, prefix):
    return obj({'version': {'const': 'evolutionary_history_evidence_option_ref_v1'}, 'library_id': _SHA256,
                'slot': {'const': slot}, 'option_id': {'type': 'string', 'pattern': '^' + prefix + '[0-9]+$'},
                'entry_sha256': _SHA256})


_THOUGHT_REF = _ref_schema('thought_pattern', 'P')
_EVIDENCE_AXIS = _ref_schema('evidence_axis', 'A')
_EVIDENCE_AXIS['properties']['option_id'] = {'const': 'A104'}
_TOOL_SELECTOR = obj({'name': _TEXT, 'resources': {'enum': ['api', 'local', 'hpc']}})
_TOOL_INFO = obj({**_TOOL_SELECTOR['properties'], 'description': _TEXT, 'instructions': _TEXT})
REVISION_ARGUMENTS = obj({'thought_pattern': _THOUGHT_REF,
                          'child_tool_info': {'type': 'array', 'items': _TOOL_SELECTOR, 'uniqueItems': True}})
_CANONICAL_SELECTION = obj({'version': {'const': SELECTION_VERSION}, 'evidence_axis': _EVIDENCE_AXIS,
                            'thought_pattern': _THOUGHT_REF,
                            'child_tool_info': {'type': 'array', 'items': _TOOL_INFO, 'uniqueItems': True}})
_REVISION_ORIGIN = obj({'version': {'const': REVISION_ORIGIN_VERSION},
                        'parent_invocation_ref': {'type': 'string', 'pattern': '^scientific_invocation_[a-f0-9]{24}$'},
                        'preparation_operation_ref': {'type': 'string', 'pattern': '^operation_[a-f0-9]{24}$'}})
_OWN_ASSIGNMENT = obj({'selection': _CANONICAL_SELECTION, 'evidence_refs': {'type': 'array', 'items': _TEXT},
                       'constraints': {'type': 'object'}, 'context': {'type': 'object'},
                       'revision_origin': _REVISION_ORIGIN},
                      required=['selection', 'evidence_refs', 'constraints', 'context'])
_HPC_ASSIGNMENT = obj({'commission_id': _TEXT, 'commission_source_ref': {'type': 'array', 'items': _TEXT},
                       'tool_request': obj({'name': _TEXT, 'resources': {'enum': ['api', 'local', 'hpc']},
                                            'arguments_json': _TEXT, 'result_reader': _TEXT, 'objective': _TEXT}),
                       'input_refs': {'type': 'array', 'items': _TEXT}}, required=['input_refs'])
CHILD_ASSIGNMENTS = {'evolutionary_history_evidence': _OWN_ASSIGNMENT, 'hpc': _HPC_ASSIGNMENT}


def _embedded(schema):
    """A tool input schema embedded in the action schema keeps its own $ref resolution."""
    import hashlib
    if any(isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node)
           for _, node in _schema_nodes(schema)) and '$id' not in schema:
        digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + digest}
    return schema


# -- the tools --------------------------------------------------------------------------------------------------


def _invalid(ctx, name, error):
    """The old ``execute`` outcome of an argument or reference error: ``invalid`` with its feedback."""
    return {'status': 'invalid', 'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                         **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}


def validate_tool_name(tool_name):
    """The old ``scientific_operations.validate_tool_name``."""
    if tool_name == 'sequence.align':
        raise ContractError('a104_new_sequence_comparison_requires_shared_parent')


async def selected_tool(arguments, ctx):
    """One of the selected actual tools of the pinned selection, on the A104 tool registry."""
    name = arguments['tool']
    try:
        validate_tool_name(name)
    except ValueError as error:
        return _invalid(ctx, name, error)
    registry = ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    permitted = ({'permitted_record_refs': arguments['permitted_record_refs']}
                 if name in PERMITTED_RECORD_TOOLS else {})
    outcome = registry.execute_async(name, arguments['arguments'], scope=arguments['scope'],
                                     operation_key=ctx.operation_key, **permitted)
    return await outcome if inspect.isawaitable(outcome) else outcome


def process_lookup(arguments, ctx):
    """``process.search``, ``process.entry`` or ``process.sources`` on the frozen process library."""
    return EvolutionaryHistoryEvidenceLibrary(ctx.settings['process_library_directory']).execute(
        arguments['name'], arguments['arguments'])


def knowledge_lookup(arguments, ctx):
    """``knowledge.search``, ``knowledge.entry`` or ``knowledge.read`` on the frozen tool knowledge."""
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['name'], arguments['arguments'])


def _resolved_tools(selection, tool_library):
    """The old ``_tool_resolution``: the selected tools with their actual contracts."""
    entries = tool_library.resolve_invocations(selection['child_tool_info'])
    if any(entry['name'] in {*COMMON_TOOL_NAMES, 'process.revise'} for entry in entries):
        raise ContractError('scientific_primitive_uses_common_tool_name')
    return entries


def process_revise(arguments, ctx):
    """The old ``process.revise``: prepare a pinned thought pattern and selected tools for a new child. Changes
    nothing else."""
    try:
        selection = validate_selection(arguments['selection'])
        revise = arguments['arguments']
        validate_schema(revise, REVISION_ARGUMENTS)
        process = EvolutionaryHistoryEvidenceLibrary(ctx.settings['process_library_directory'])
        tool_library = ScientificToolLibrary(ctx.settings['tool_library_directory'])
        fields = selection_fields(selection)
        proposed = validate_selection({'version': SELECTION_VERSION, 'evidence_axis': selection[fields[0]],
                                       'thought_pattern': revise['thought_pattern'],
                                       'child_tool_info': tool_library.resolve_tool_info(revise['child_tool_info'])})
        for key in fields[:2]:
            if proposed[key]['library_id'] != process.as_record()['library_id']:
                raise ContractError('scientific_selection_library_mismatch')
            process.resolve(proposed[key])
        _resolved_tools(proposed, tool_library)
        child_selection = validate_child_selection({'version': CHILD_SELECTION_VERSION,
                                                    'parent_selection_sha256': scientific_digest(selection),
                                                    'selection': proposed})
        operation_ref = identity('operation', {'key': ctx.operation_key, 'name': 'process.revise',
                                               'arguments': revise})
        origin = validate_revision_origin({
            'version': REVISION_ORIGIN_VERSION,
            'parent_invocation_ref': scientific_invocation_ref(ctx.run_id, ((ctx.binding_path, ctx.episode_id),)),
            'preparation_operation_ref': operation_ref})
    except ValueError as error:
        return _invalid(ctx, 'process.revise', error)
    return {'status': 'completed', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': child_selection, 'revision_origin': origin, 'feedback': None}


def reason(arguments, ctx):
    """The committed scientific interpretation: the model's typed reasoning into the Store."""
    try:
        result = ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)
    except CustodyError as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': 'reasoning_names_an_unheld_record',
                             'detail': str(error)}}
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': result, 'feedback': None}


def _phylogeny_invalid(error):
    """The old ``A104ToolRegistry.execute_async`` outcome of an argument, reference or measurement error."""
    detail = getattr(error, 'detail', {})
    if str(error) == 'a104_measured_placement_required':
        detail = {**detail, 'recovery': 'Use the measurement_ref returned by phylogeny.measure_placement '
                  'for each placement operand.'}
    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'code': str(error), 'detail': detail}}


def _held(store, reference, known):
    require(reference in known, 'a104_tool_input_not_received')
    return store.get(reference)


def _measured(store, reference, scope, known):
    _held(store, reference, known)
    measured = received_measurement(store, reference)
    require(measured is not None and measured['body']['schema'] == 'a104_placement_v1',
            'a104_measured_placement_required')
    require(measured['body']['target_ref'] in scope['subject_refs'], 'a104_native_scope_conflict')
    return measured


def _published(store, body, scope, known):
    """Publish one native sheet with its native observation, then attribute every held measurement again (the
    per-use attribution sheets). Returns the completed outcome."""
    with store.transaction():
        reference = publish_measurement(store, body)
        observation = native_observation(store, reference)
        attributions, needs = refresh_attribution(store, {*known, reference}, scope)
    return {'status': 'completed', 'record_refs': [reference, observation, *attributions], 'changed_record_refs': [],
            'result': {'measurement_ref': reference, 'observation_ref': observation, 'attribution_refs': attributions,
                       'needs': needs, **body}, 'feedback': None}


def _phylogeny(name, arguments, ctx):
    """One A104 phylogeny operation (the old ``A104ToolRegistry.execute_async`` branches of ``NAMES[2:7]``) on the
    records this episode holds, in its scope."""
    store, args = ctx.store, arguments['arguments']
    try:
        validate_schema(args, PHYLOGENY_TOOLS[name][2])
        scope = store.validate_scope(arguments['scope'])
        known = set(store.refs())
        if 'native_ref' in args:
            _held(store, args['native_ref'], known)
            native = native_body(store, args['native_ref'])
            require(native is not None and native['target_ref'] in scope['subject_refs'], 'a104_native_scope_conflict')
        if name == 'phylogeny_inspect':
            body = native_body(store, args['native_ref'])
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'feedback': None,
                    'result': {'native_ref': args['native_ref'], 'pbs_job_id': body['pbs_job_id'],
                    'admission_status': 'already_authenticated_native_phylogeny; use_measurement_tools_directly',
                    'partial_execution': body['partial_execution'],
                    'missing_analysis_names': body['missing_analysis_names'],
                    'corresponding_relationships': relationship_inventory(body),
                    'analyses': [{'name': row['name'], 'purpose': row['purpose'],
                        'native_splits': [{**split, 'split_index': i} for i, split in enumerate(row['tree_summary']['splits'])],
                        'members': next(binding['members'] for binding in body['bindings'] if binding['name'] == row['name'])}
                        for row in body['result']['analyses']]}}
        if name == 'phylogeny_measure_placement':
            body = placement(store, args['native_ref'], args['analysis'], args['split_index'], known)
        elif name == 'phylogeny_compare_histories':
            body = history_comparison(store, args['native_ref'], args['family_analysis'], args['organismal_analysis'],
                                      args['tip_ids'], known)
        elif name == 'phylogeny_clade_functions':
            _measured(store, args['placement_ref'], scope, known)
            body = clade_composition(store, args['placement_ref'], known)
        elif name == 'phylogeny_compare_placements':
            for reference in args['placement_refs']:
                _measured(store, reference, scope, known)
            body = compare_placements(store, args['placement_refs'], known)
        else:
            measured = received_measurement(store, _held(store, args['measurement_ref'], known)['id'])
            require(measured is not None, 'a104_history_explanation_requires_actual_phylogeny')
            require(measured['body']['target_ref'] in scope['subject_refs'], 'a104_native_scope_conflict')
            with store.transaction():
                reference = publish_explanation(store, measured, args['grade'], args['support_refs'])
                attributions, needs = refresh_attribution(store, {*known, reference}, scope)
            return {'status': 'completed', 'record_refs': [reference, *attributions], 'changed_record_refs': [],
                    'result': {'explanation_ref': reference, 'attribution_refs': attributions, 'needs': needs},
                    'feedback': None}
        return _published(store, body, scope, known)
    except (ValueError, KeyError, TypeError, IndexError) as error:
        return _phylogeny_invalid(error)


def phylogeny_inspect(arguments, ctx):
    return _phylogeny('phylogeny_inspect', arguments, ctx)


def phylogeny_measure_placement(arguments, ctx):
    return _phylogeny('phylogeny_measure_placement', arguments, ctx)


def phylogeny_compare_histories(arguments, ctx):
    return _phylogeny('phylogeny_compare_histories', arguments, ctx)


def phylogeny_clade_functions(arguments, ctx):
    return _phylogeny('phylogeny_clade_functions', arguments, ctx)


def phylogeny_compare_placements(arguments, ctx):
    return _phylogeny('phylogeny_compare_placements', arguments, ctx)


def phylogeny_explain_history(arguments, ctx):
    return _phylogeny('phylogeny_explain_history', arguments, ctx)


TOOLS = {'selected_tool': selected_tool, 'process_lookup': process_lookup, 'knowledge_lookup': knowledge_lookup,
         'process_revise': process_revise, 'reason': reason,
         'phylogeny_inspect': phylogeny_inspect, 'phylogeny_measure_placement': phylogeny_measure_placement,
         'phylogeny_compare_histories': phylogeny_compare_histories,
         'phylogeny_clade_functions': phylogeny_clade_functions,
         'phylogeny_compare_placements': phylogeny_compare_placements,
         'phylogeny_explain_history': phylogeny_explain_history}


# -- the offer ----------------------------------------------------------------------------------------------------


def compose_instructions(*, replaces_default, tool_knowledge, launch_library):
    """The old ``task_instructions.compose_instructions`` with its inputs as parameters: the goal text replaces the
    default instructions when every evidence-axis entry of the library is an instruction entry, else it is appended;
    then the reasoning-commit requirement, the tool-knowledge instructions and the launch-library instructions where
    present. The redelivery, wait, native-event and exchange-protocol paragraphs describe actions and protocols that
    do not exist now and are not carried."""
    instructions = GOAL if replaces_default else INSTRUCTIONS + '\n' + GOAL
    instructions += '\n' + REASONING_COMMIT_REQUIREMENT
    if tool_knowledge:
        instructions += KNOWLEDGE_INSTRUCTIONS
    if launch_library:
        instructions += LAUNCH_INSTRUCTIONS
    return instructions + GRADING_SECTION + RETURN_GUIDANCE


def selected_tool_entries(summary, settings):
    """The old ``catalog``: the selected tools of the pinned selection whose route is direct, without their
    instructions and routes."""
    tool_library = ScientificToolLibrary(settings['tool_library_directory'])
    resolved = _resolved_tools(summary['selection'], tool_library)
    direct = [row for row in resolved if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
    return [{key: value for key, value in row.items() if key not in {'instructions', 'invocation_route'}}
            for row in direct]


def _common_entries(settings):
    entries = [entry for entry in process_catalog()]
    entries.append({'name': 'process.revise', 'description': REVISION_DESCRIPTION,
                    'input_schema': REVISION_ARGUMENTS})
    if 'tool_knowledge_directory' in settings:
        entries.extend(knowledge_catalog())
    return entries


def _child_option(slot, assignment_schema):
    properties = {'kind': {'type': 'string', 'const': 'episode_child'},
                  'role': {'type': 'string', 'const': slot},
                  'objective': {'type': 'string', 'minLength': 1, 'description': 'The child episode objective.'},
                  'purpose': {'type': 'string', 'minLength': 1,
                              'description': 'What the child result is for, for the child.'},
                  'scope': {'type': 'object', 'description': 'A Store scope within this scope.'},
                  'initial_report': {'type': 'object', 'description': 'Values for the child to start from.'},
                  'assignment': assignment_schema,
                  'return_fields': {'type': 'array', 'items': {'enum': list(RETURN_FIELDS[slot])},
                                    'description': 'The selectable result fields wanted from the child.'}}
    return {**obj(properties, required=[name for name in properties if name != 'initial_report']),
            'description': CHILD_PURPOSE[slot]}


def decision_schema(summary, settings):
    """The action schema of this decision: every offered action, built from the pinned selection and the settings.
    The committed interpretation is the tool ``reason``: the arguments of a tool whose schema is composed travel as
    JSON text, and the Store's reasoning schema sent as output schema itself has more enum values than the model
    endpoint takes in one schema."""
    commit = obj({'commit': summary['reasoning_schema'],
                  'evidence_processing': obj({'kind': {'enum': ['no_applicable_evidence']}})}, required=['commit'])
    options = [{**obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': 'reason'},
                       'arguments': commit}),
                'description': REASONING_COMMIT_REQUIREMENT},
               ]
    entries = [*selected_tool_entries(summary, settings), *_common_entries(settings), *phylogeny_entries()]
    for entry in sorted(entries, key=lambda item: item['name']):
        options.append({**obj({'kind': {'type': 'string', 'const': 'tool'},
                               'tool': {'type': 'string', 'const': entry['name']},
                               'arguments': _embedded(entry['input_schema'])}),
                        'description': entry['description']})
    for slot in OFFERED_CHILDREN:
        options.append(_child_option(slot, CHILD_ASSIGNMENTS[slot]))
    return obj({'selection': {'anyOf': options}})


def decide(summary, feedback, ctx):
    settings = ctx.settings
    schema = decision_schema(summary, settings)
    process = EvolutionaryHistoryEvidenceLibrary(settings['process_library_directory'])
    selection = summary['selection']
    axis_ref, thought_ref, _ = (selection[name] for name in selection_fields(selection))
    axes = [header['option_ref'] for header in process.headers() if header['option_ref']['slot'] == 'evidence_axis']
    replaces_default = bool(axes) and all(process.resolve(ref).get('entry_version') == INSTRUCTION_VERSION
                                          for ref in axes)
    thought = process.resolve(thought_ref)
    context = {'goal': summary['goal'], 'scope': summary['scope'], 'purpose': summary['purpose'],
               'initial_report': summary['initial_report'], 'evidence_task': summary['evidence_task'],
               'evolutionary_history_evidence': {
                   'selection': {**selection, 'child_tool_info': [
                       {key: row[key] for key in ('name', 'description', 'resources')}
                       for row in selection['child_tool_info']]},
                   'initial_selection_sha256': summary['initial_selection_sha256'],
                   'evidence_axis': instruction_view(process.resolve(axis_ref)),
                   'thought_pattern': {name: thought[name] for name in
                                       ('id', 'name', 'description', 'use_when', 'live_alternatives',
                                        'decision_guidance', 'outcome_contingencies', 'boundary') if name in thought},
                   'assignment': {name: summary[name] for name in
                                  ('proposed_annotation_ref', 'evidence_refs', 'constraints', 'context',
                                   'revision_origin')},
                   'permitted_children': summary['permitted_children']},
               'working_state': summary['working_state'],
               'visible_record_refs': summary['visible_record_refs'],
               'current_credit': summary['credit_view']['credit'],
               'current_evidence_vector': {name: summary['credit_view'][name]
                                           for name in ('target_sheets', 'source_contribution_count')
                                           if name in summary['credit_view']},
               'credit_binding': summary['credit_binding'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               'action_yields': summary['controller'],
               'units': summary['unit_index'],
               'last_local_outcome': summary['last_outcome'],
               'feedback': feedback if feedback is not None else summary['last_feedback'],
               'a104_sheets': summary['a104_sheets'], 'a104_targets': summary['a104_targets'],
               'child_returns': summary['child_returns'],
               'child_options': {slot: CHILD_PURPOSE[slot] for slot in OFFERED_CHILDREN},
               'tools': [{key: value for key, value in entry.items() if key != 'input_schema'}
                         for entry in selected_tool_entries(summary, settings)]}
    if 'tool_knowledge_directory' in settings:
        context['tool_knowledge'] = ToolKnowledge(settings['tool_knowledge_directory']).context()
    if 'launch_instruction_directory' in settings:
        context['launch_instruction_library'] = LaunchInstructions(settings['launch_instruction_directory']).context()
    instructions = compose_instructions(replaces_default=replaces_default,
                                        tool_knowledge='tool_knowledge' in context,
                                        launch_library='launch_instruction_library' in context)
    return ModelRequest(MODEL_ROLE, instructions, context, strict_output_schema(schema, **TRANSPORT))


def _unit(selection, summary, records):
    kind = selection['kind']
    if kind == 'tool':
        name, arguments = selection['tool'], selection['arguments']
        if name == 'reason':
            payload = arguments['commit']
            commit_schema = summary['reasoning_schema']
            if (set(commit_schema.get('required', commit_schema['properties'])) <= set(payload)
                    <= set(commit_schema['properties']) and all(value == [] for value in payload.values())
                    and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
                raise ValueError('empty_reasoning_commit')
            return ToolCall('reason', {'commit': payload, 'scope': summary['scope']})
        if name in PROCESS_LOOKUPS:
            return ToolCall('process_lookup', {'name': name, 'arguments': arguments})
        if name in KNOWLEDGE_LOOKUPS:
            return ToolCall('knowledge_lookup', {'name': name, 'arguments': arguments})
        if name in PHYLOGENY_NAMES:
            return ToolCall(PHYLOGENY_NAMES[name], {'arguments': arguments, 'scope': summary['scope']})
        if name == 'process.revise':
            return ToolCall('process_revise', {'arguments': arguments, 'selection': summary['selection']})
        call = {'tool': name, 'arguments': arguments, 'scope': summary['scope']}
        if name in PERMITTED_RECORD_TOOLS:
            call['permitted_record_refs'] = list(records.refs())
        return ToolCall('selected_tool', call)
    if kind == 'episode_child':
        return ChildCall(selection['role'], {name: value for name, value in selection.items()
                                             if name not in ('kind', 'role')})
    raise ValueError('a104_selection_kind_unknown:' + str(kind))


def action(response, summary, records, ctx):
    schema = decision_schema(summary, ctx.settings)
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('a104_decision_response_must_be_exactly_selection')
        selection = decode_strict_output(dict(response), schema, **TRANSPORT)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        return _unit(selection, summary, records)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
