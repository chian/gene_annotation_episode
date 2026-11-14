"""Original detached saved-return and source-qualification presentation."""
from collections.abc import Mapping
from copy import deepcopy
import json

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
        from gene_annotation_episode.episodic_workflow.root.communication import plain
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


