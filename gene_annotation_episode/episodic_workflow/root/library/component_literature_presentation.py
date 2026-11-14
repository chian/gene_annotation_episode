"""Original supplied-state component literature presentation; no runtime ownership selection."""
from collections.abc import Mapping
from copy import deepcopy
from .literature_declared_task_text import EXPERIMENTAL_TASK
from .literature_prompt_composition import render_literature_experimental_prompt
from .literature_task_selection import A105_ASSAY_SELECTION_TASK

SOURCE_AVAILABILITY = """For literature acquisition, inspect the returned native availability metadata. Europe PMC full-text XML serves its open-access subset; presence in PMC or free HTML/PDF access does not by itself establish XML availability. Preserve the actual retrieval failure separately from scientific absence, and select a usable representation or another relevant source when appropriate."""

SOURCE_SCOPE = """Page and reader children can use only their assigned Source and its derived Sources. A known or received sibling dataset is outside that reading assignment, even when it describes the same experiment. Keep a calculation needing separate evidence and data Sources with a literature, strategy or search owner that actually holds both. A bounded reader can instead return source-local observations or select operands entirely within its own Source. Before delegating, preserve the inputs the child can actually read. component_axis_source_access reports real access rejections to the owner on its next decision; these are operational needs, not scientific absence or opposition. Repeating a rejected read does not widen its assignment."""


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
