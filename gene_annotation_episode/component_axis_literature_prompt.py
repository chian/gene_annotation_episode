"""Select the literature lead for explicitly requested A107/A110 components.

This presentation adapter leaves source selection, numerical methods, saved
returns and the scientific continuation controller with their existing owners.
Explicit component requests and selected saved return types identify the task;
available operations or capabilities alone do not select it.
"""
from collections.abc import Mapping
from copy import deepcopy
import json

from .literature_experimental_prompt import EXPERIMENTAL_TASK, render_literature_experimental_prompt
from .literature_task_selection import A105_ASSAY_SELECTION_TASK


SOURCE_AVAILABILITY = """For literature acquisition, inspect the returned native availability metadata. Europe PMC full-text XML serves its open-access subset; presence in PMC or free HTML/PDF access does not by itself establish XML availability. Preserve the actual retrieval failure separately from scientific absence, and select a usable representation or another relevant source when appropriate."""

SOURCE_SCOPE = """Page and reader children can use only their assigned Source and its derived Sources. A known or received sibling dataset is outside that reading assignment, even when it describes the same experiment. Keep a calculation needing separate evidence and data Sources with a literature, strategy or search owner that actually holds both. A bounded reader can instead return source-local observations or select operands entirely within its own Source. Before delegating, preserve the inputs the child can actually read. component_axis_source_access reports real access rejections to the owner on its next decision; these are operational needs, not scientific absence or opposition. Repeating a rejected read does not widen its assignment."""


FACT_CONTRACT_TASK = """Exact saved child return contracts

For this episode's declared contract-information interface, request_context with view=composition_information, operation=episode.return_contract and arguments containing the permitted child's role and the requested recorded-fact source returns its complete frozen type and meaning. This is information within the pending decision, not an action or a child launch.

Select a saved return in your child schema using a top-level field containing only {"$ref":"episode-fact:<source>"}, replacing <source> with the actual declared source name. For example, {"$ref":"episode-fact:committed_record_refs"} selects that recorded-fact type. The host expands this explicit reference to the complete closed type and supplies the saved values; leave that field out of initial_report_json. Choose your own interpretation fields separately and keep them explicit, required and closed. An open object or array item such as {"type":"object"} does not request a saved type, including when its field names an x-source. Use the original complete declaration or the explicit top-level fact reference rather than an incomplete placeholder. Select only facts needed for the assigned question."""


def with_fact_contract_instructions(rendered, state):
    """Present an already enabled interface to generic/root TASK renderers too."""
    prefix = "TASK\n\n"
    access = state.get('component_axis_source_access')
    access_title = 'Recorded source inspections and access'
    if (isinstance(access, Mapping)
            and access.get('version') == 'component_axis_source_access_v1'
            and rendered.startswith(prefix) and access_title not in rendered):
        from .communication import plain
        rendered = (prefix + access_title + '\n\n'
            + json.dumps(plain(access), sort_keys=True, ensure_ascii=False, indent=2)
            + '\n\n' + rendered[len(prefix):])
    recorded = _recorded_components(state)
    recorded_title = 'Recorded component results and specific unresolved operands'
    if recorded and rendered.startswith(prefix) and recorded_title not in rendered:
        rendered = (prefix + recorded_title + '\n\n'
            + json.dumps(recorded, sort_keys=True, ensure_ascii=False, indent=2)
            + '\n\n' + rendered[len(prefix):])
    rejection_title = 'Recorded observation subjects for the rejected finding'
    if (isinstance(access, Mapping)
            and access.get('version') == 'component_axis_source_access_v1'
            and rendered.startswith(prefix) and rejection_title not in rendered):
        rejected = _finding_subject_rejections(state.get('last_local_outcome'))
        if rejected:
            rendered = (prefix + rejection_title + '\n\n'
                + json.dumps(rejected, sort_keys=True, ensure_ascii=False, indent=2)
                + '\n\n' + rendered[len(prefix):])
    if (state.get("contract_information_profile") != "operation_contract_information_v1"
            or not rendered.startswith(prefix) or FACT_CONTRACT_TASK in rendered):
        return rendered
    return prefix + FACT_CONTRACT_TASK + "\n\n" + rendered[len(prefix):]


def _finding_subject_rejections(outcome):
    """Keep callable subjects from own rejection/history, without new receipt.

    Traverse only the host's own-outcome and selected history envelopes. Source
    text or arbitrary provider response objects are not validation feedback.
    """
    pending, result, seen = [outcome], [], set()
    while pending:
        current = pending.pop()
        if not isinstance(current, Mapping):
            continue
        for error in current.get('errors') or ():
            if (not isinstance(error, Mapping)
                    or error.get('code') != 'finding_source_subject_not_in_observation'
                    or 'observation_subject_refs' not in error
                    or 'observation_source_subject_refs' not in error):
                continue
            key = json.dumps(error, sort_keys=True)
            if key not in seen:
                seen.add(key)
                result.append(deepcopy(error))
        content = current.get('result')
        if (isinstance(content, Mapping) and content.get('view') == 'records'
                and 'total_prior_decisions' in content):
            pending.extend(row.get('outcome') for row in content.get('records', ())
                if isinstance(row, Mapping))
    return result


def _recorded_components(state):
    """Foreground only cells and per-use qualifications already in this view."""
    sheets = state.get('component_axis_scoring_sheets', {})
    if not isinstance(sheets, Mapping):
        return []
    result = []
    for axis in ('A107', 'A110'):
        sheet = sheets.get(axis)
        if not isinstance(sheet, Mapping):
            continue
        findings = [{key: deepcopy(row[key]) for key in ('sheet_ref', 'assessment_state',
            'experimental_bindings', 'components', 'experiment_assessment') if key in row}
            for row in sheet.get('numerical_results', ())]
        qualifications = []
        for row in sheet.get('tool_qualifications', ()):
            use = row.get('result', {})
            qualifications.append({**{key: deepcopy(row[key]) for key in ('source_ref',
                'current', 'changed_received_operand_refs', 'scope', 'target_ref',
                'target_regions', 'qualification_kind') if key in row},
                'recorded_use': {key: deepcopy(use[key]) for key in ('state', 'sheet_ref',
                    'selected_components', 'missing', 'missing_components', 'limitation',
                    'source_assayed_subject_ref', 'reaction_ref') if key in use}})
        if findings or qualifications:
            result.append({'axis': axis, 'recorded_results': findings,
                'particular_uses': qualifications,
                'meaning': 'Check assessment_state, each use\'s current flag and changed operands '
                    'before reusing received results. Superseded or stale uses require the '
                    'applicable current assessment. Their existence is not functional '
                    'support or completion of a different question. Missing operands remain '
                    'specific to each use; source and target scope remain separate.'})
    return result


COMPONENT_READING_TASK = """Reuse applicable recorded components, exact source witnesses and prior inspections before selecting more work. Choose an additional read or calculation to address a particular unresolved operand or scientific question; revisiting a passage remains available when needed. A completed read is not a completed biological assessment. An unavailable cell describes its selected inputs, not everything in a paper.

Establish the actual assayed molecule or construct, organism, experimental system, endpoint, units, controls, conditions, uncertainty and repetition basis. Keep source quantities, interpreted models and target application separate. Select source spans and scientific meanings; the original readers, validators and graders perform the calculations. Preserve missing calibration, identity, measurements and dependence. Repeated representations are not independent evidence. No overall reliability, transfer weight or annotation probability is defined here.

Return the requested saved typed information with its scope and limitations. Source reading, bookkeeping and repeated results add no scientific credit; the existing controller owns continuation."""


PARTNER_LEAD = """Investigate the assigned source evidence about a particular molecule's dependence on a particular partner. Select the relevant omission, addback and control observations, their experimental meanings and the applicable partner component readers and graders. Return the requested saved partner components with their actual subject, endpoint, conditions, uncertainty, provenance and unresolved inputs. Required partnership, genomic presence, coexpression, physical interaction and demonstrated function are distinct questions; this source investigation does not establish the other questions automatically.

literature.partner.source.populate reads selected literal source spans directly, without a prepared numerical dataset. literature.partner.populate uses a compatible retained selection dataset. Select the route whose actual inputs are available, preserve missing measurements and use the existing operation contract for complete operands."""

REACTION_LEAD = """Investigate the assigned source evidence about reaction predictions, measured ratios or resource constraints. Select the relevant measurements and source meanings, then use the applicable reaction component readers and graders. Return the requested saved components with their actual molecule, chemical species, endpoint, units, conditions, provenance, dependence and unresolved inputs. Chemical bookkeeping, measured molecular activity and physiological feasibility are separate conclusions.

literature.reaction.source.populate accepts exact reported-number and source-unit selectors directly; the host retains the selection recipe and uses the original native reader and component calculator. Choose this route for usable paper evidence without a prepared numerical dataset. Predictions and resource-model parameters remain explicitly interpreted rather than measured values.

For literature.reaction.populate, source_ref identifies the evidence source. data_source_ref identifies a compatible retained measurement dataset or native source-selection recipe. Supported retained dataset versions are a110_source_reaction_measurements_v1 and a110_source_reaction_measurements_v2; a110_source_reaction_selection_v1 holds native source selectors. A supplied compatible dataset can be used directly, without re-extracting its numbers into selectors. Declared synthetic operands can yield conditional components while retaining synthetic origin, unknown biological applicability and unresolved target correspondence. Their calculation does not require first establishing chemical identity or protein activity. A declared chemical equation or formula panel is not automatically a measurement dataset. The existing operation permits data_source_ref=null when no supported dataset or source-selection route is available, preserving unavailable components and their missing reasons. Do not invent measurements to fill them. Use the actual source and operation contracts to decide what is supported."""

REACTION_VIEW_MEANING = """The numerical and semantic return views have different input requirements. A v1 measurement dataset supplies literature_reaction_cells but has no retained source-bound model/resource meanings for literature_reaction_semantic_cells. Repeating that v1 population or adding literal identity bindings does not create the semantic view. For requested semantic cells, select an actually received v2 dataset or use literature.reaction.source.populate with the supported native source selectors and their source-bound meanings. Unsupported identities remain unknown; a conditional model definition is separate from a measured value. If the available evidence cannot support a meaning, preserve that missing reason. These are views of related evidence, not independent confirmations."""

A107_SOURCE_LEAD = """Investigate the assigned source-reading question for A107, required partner presence and coexpression. Establish what the supplied source actually contains: partner-requirement experiments, genomic records, expression measurements or relevant context. These are different source questions. A supplied expression table can be inspected without finding an omission/addback experiment or establishing functional partnership first. Preserve declared feature and sample identities, conditions, quantity meanings, censoring, calibration, provenance and unresolved biological correspondence. Select the available reading, reasoning and narrower investigations according to the actual question. Return the requested typed findings and source-anchored records needed by the scientific parent for its next decision. This reading question does not by itself establish activity, necessity, target expression or annotation support."""

A110_SOURCE_LEAD = """Investigate the assigned source-reading question for A110, biochemical feasibility and chemical/resource accounting. Establish whether the supplied source contains declared chemical equations, measured ratios, model predictions, resource observations or relevant context. Keep those meanings separate and preserve the actual species, quantities, units, conditions, model assumptions, provenance and missing inputs. Inspecting a declared equation panel does not require an activity experiment or make it a measurement dataset. Choose available reading, reasoning and narrower investigations according to the actual question, and return the requested typed findings and anchored source records needed by the scientific parent. Balance, a supplied reagent quantity and a source claim do not by themselves establish physiological feasibility or target activity."""


def component_axis_source_origin(services, context):
    """Read only the nearest admitted scientific ancestor's axis metadata.

    No axis is inferred from a goal, source label or available capability. The
    result is task provenance, never scientific evidence or a selected assay.
    """
    from .scientific_process_records import SELECTION_VERSION
    workflow = getattr(services, 'workflow', None)
    store = getattr(workflow, 'store', None)
    if store is None or context.run_id != workflow.run_id:
        return None
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='runtime_episodes'").fetchone() is None:
        return None
    for index in range(len(context.path)-2, -1, -1):
        if context.path[index][0] != 'scientific_process':
            continue
        row = store.db.execute("SELECT episode_id, "
            "json_extract(request,'$.message.episode_assignment.selection.version') AS version, "
            "json_extract(request,'$.message.episode_assignment.selection.evidence_axis.option_id') AS axis "
            "FROM runtime_episodes WHERE run_id=? AND json(path)=json(?)",
            (context.run_id, json.dumps(context.path[:index+1]))).fetchone()
        if row is not None and row['version'] == SELECTION_VERSION and row['axis'] in {'A107', 'A110'}:
            return {'version': 'admitted_component_axis_source_origin_v1',
                'evidence_axis': row['axis'], 'scientific_parent_episode_id': row['episode_id'],
                'meaning': 'Original admitted scientific commission; source-reading task provenance only'}
        return None
    return None


def _selected_family(state):
    assignment = state.get("literature_assignment", {})
    if not isinstance(assignment, Mapping):
        return None
    work = state.get("literature_experimental_work", {})
    if isinstance(work, Mapping) and (work.get("evidence_axis") in {"A105", "A106", "A108"}
            or work.get("aspect") == "reference_evidence_parent"):
        return None
    selected = {key for key, value in assignment.items()
                if key.startswith("requested_") and value}
    if selected and selected <= {"requested_partner_components"}:
        return "partner"
    if selected and selected <= {"requested_reaction_components", "requested_reaction_native_positions"}:
        return "reaction"
    if not selected:
        # A v1 source assignment need not repeat component selectors. Its
        # frozen return contract can still explicitly request numerical facts.
        # Use those declared sources, never field names or available facts.
        form = state.get('requested_form', {})
        properties = form.get('properties', {}) if isinstance(form, Mapping) else {}
        if not isinstance(properties, Mapping):
            properties = {}
        sources = {field['x-source'] for field in properties.values()
            if isinstance(field, Mapping) and isinstance(field.get('x-source'), str)
            and field['x-source'].startswith('literature_')}
        if sources and sources <= {'literature_partner_cells'}:
            return 'partner'
        if sources and sources <= {'literature_reaction_cells',
                'literature_reaction_semantic_cells', 'literature_reaction_native_observations'}:
            return 'reaction'
        origin = state.get('component_axis_source_origin', {})
        axis = origin.get('evidence_axis') if isinstance(origin, Mapping) else None
        if axis in {'A107', 'A110'}:
            return axis + '_source'
    return None


def render_component_axis_literature_prompt(state, instructions, *, lookup_results=()):
    """Focus the task view without changing operations, schemas or receipts."""
    family = _selected_family(state)
    view = state
    if family is not None and state.get('contract_information_profile') == 'operation_contract_information_v1':
        view = deepcopy(state)
        axis_family = 'partner' if family in {'partner', 'A107_source'} else 'reaction'
        preferred, other = [], []
        for tool in view.get('tools', ()):
            name = tool.get('name', '')
            if name.startswith('literature.') and not name.startswith('literature.' + axis_family + '.'):
                # All names remain discoverable; the actual complete contracts
                # and argument transport stay with the original host binding.
                tool['description'] = 'Available; request its full meaning and operands through episode.operation_contract.'
                tool.pop('input_schema', None)
                other.append(tool)
            else:
                preferred.append(tool)
        view['tools'] = preferred + other
    rendered = render_literature_experimental_prompt(
        view, instructions, lookup_results=lookup_results)
    prefix = "TASK\n\n" + A105_ASSAY_SELECTION_TASK
    if family is None or not rendered.startswith(prefix):
        return rendered
    lead = {'partner': PARTNER_LEAD, 'reaction': REACTION_LEAD,
        'A107_source': A107_SOURCE_LEAD, 'A110_source': A110_SOURCE_LEAD}[family]
    if family == 'reaction':
        lead += '\n\n' + REACTION_VIEW_MEANING
    rendered = rendered.replace(EXPERIMENTAL_TASK, COMPONENT_READING_TASK)
    return "TASK\n\n" + lead + "\n\n" + SOURCE_AVAILABILITY + "\n\n" + SOURCE_SCOPE + rendered[len(prefix):]
