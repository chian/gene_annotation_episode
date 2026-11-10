"""Versioned scientific ownership of comparative and experimental structure.

This contract contains no execution policy or new scientific score. Historical
A102/A111 publications and calculation versions keep their original meanings.
"""
from copy import deepcopy

from .communication import plain
from .domain import ContractError
from .evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, validate_instruction_entry


VERSION = 'a102_structural_evidence_v2'
NAME = 'Structural evidence'
DESCRIPTION = ('Investigate comparative and experimentally determined structural evidence, '
    'including model identity, correspondence, function-relevant features and local validation.')
COMPARATIVE_TASKS = ('structural_discovery', 'native_comparison',
    'functional_feature_geometry', 'functional_contrast', 'reference_attribution',
    'local_trait_attribution', 'interface_constraints')
EXPERIMENTAL_TASKS = ('experimental_source_discovery', 'experimental_model_identity',
    'experimental_feature_geometry', 'experimental_local_validation',
    'experimental_assessment')
SHARED_TASKS = ('model_inventory', 'target_model_correspondence', 'synthesis')
TASKS = (*SHARED_TASKS, *COMPARATIVE_TASKS, *EXPERIMENTAL_TASKS)

INSTRUCTIONS = """Investigate structural evidence relevant to the supplied molecule and biological question. Start from the supplied sequence, selected files or snippets, preserving boundaries, completeness and known context. Use structural comparison, experimental structural evidence, or both according to the uncertainty being addressed. Either path can establish useful findings independently. Possible functions can emerge from the evidence and be compared or revised.

Establish model identity, experimental or predicted origin, construct, molecular state, partners, preparation and source provenance. Keep the assayed molecule separate from the supplied target and establish the correspondence needed for each transfer. Preserve chains, residue numbering, insertion codes, alternate locations, missing coordinates and mapped extent. A fragment, domain or subunit finding retains that scope.

For comparative evidence, retain native structural correspondence and its actual maps, transformations and measured extent. Examine function-relevant features, interfaces, local traits and relevant alternative explanations where useful. Reuse qualified retained comparisons. Keep native correspondence, feature-qualified support and contrasts as separately named results; a fold resemblance alone does not establish substrate specificity or whole-complex activity. Computational operations use the configured execution and result-publication services.

For experimental evidence, discover and read the relevant publications and deposited records using the available search and source-reading operations. Establish what the experiment and its selected model support about a declared molecular feature or state. Distinguish diffraction or other measured data, model fitting, coordinate-derived geometry and the authors' mechanistic interpretation. Declare the feature panel and physical selections; inspect matching entry and revision metadata for local validation. Preserve unresolved assignments, coordinate uncertainty and unsupported measurement types. Deposited occupancy is a model parameter, not an inferred population frequency.

Use the available structure population operation through a literature child for selected-model geometry and matching local validation. Request and return the applicable saved numerical components with units, bounds, conditions and missing reasons. The implemented local-fit reader uses residue RSCC; another method's validation metric needs its own supported reader and meaning. Missing local validation can leave combined source geometry unavailable while measured geometry remains useful. A contact is structural evidence; affinity, reaction rate and causal effects require their own experimental findings.

Connect repeated representations through the original experiment, dataset, model revision and source identities. Retain assessment revisions and common measurement ownership. Multiple feature questions, model copies, conformers, validation records, database records and papers about one experiment do not become independent experiments. Unknown identity leaves dependence unresolved. Retain useful distinct observations without adding their unlike scores.

Keep one A102 owner for this structural investigation. Scientific descendants continue the same structural responsibility. When shared operations are available, send the immediate parent specific missing operands or received findings relevant to its decision. That parent chooses within its own investigation options or relays the need upward; publication does not commission response work. Use the actual configured tool information and available episode roles to choose operations. Return authenticated comparative records and experimental numerical cells, their dependence, biological scope, limitations and unresolved information needs. Retain typed, source-bound scientific findings through the available evidence operations so that experimental and shared-task progress reflects findings received, not operation counts. Controller progress is separate from the scientific components; there is no combined comparative-plus-experimental scalar."""


def merged_entry(comparative, experimental):
    """Create a new instruction entry; the two input entries remain unchanged."""
    if comparative.get('id') != 'A102' or experimental.get('id') != 'A111':
        raise ContractError('a102_merge_requires_original_axis_entries')
    return validate_instruction_entry({'entry_version': INSTRUCTION_VERSION,
        'id': 'A102', 'slot': 'evidence_axis', 'name': NAME, 'description': DESCRIPTION,
        'investigation_instructions': INSTRUCTIONS,
        'evidence': deepcopy([*comparative['evidence'], *experimental['evidence']])})


def is_merged_entry(entry):
    """Bind behavior to the published contract, not a model-authored mode flag."""
    return (entry.get('entry_version') == INSTRUCTION_VERSION
        and entry.get('id') == 'A102' and entry.get('slot') == 'evidence_axis'
        and entry.get('name') == NAME and entry.get('description') == DESCRIPTION
        and entry.get('investigation_instructions') == INSTRUCTIONS)


def task_context(task):
    if task not in TASKS:
        raise ContractError('a102_unknown_structural_evidence_task')
    path = ('comparative' if task in COMPARATIVE_TASKS else
        'experimental' if task in EXPERIMENTAL_TASKS else 'shared')
    return {'version': VERSION, 'name': task, 'evidence_path': path,
        'allowed_tasks': list(TASKS),
        'scientific_output': 'Separate comparative records and experimental numerical cells; '
            'preserve target correspondence, source identity, dependencies and unknowns.',
        'progress': ('native_correspondence' if path == 'comparative' else
            'received_retained_scientific_findings'),
        'communication': 'Scientific descendants remain A102. Publish acquired information and '
            'missing-information requests to the shared parent.'}


def finding_progress():
    from .investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    return ScientificFindingProgress(FindingProgressPolicy(finding_unit=1))


def credit_projector(assignment):
    """Choose a controller from the original commission, never sum unlike units.

    A direct commission with only the merged axis selected is a shared task.
    A malformed explicit task is rejected instead of silently changing units.
    """
    task = plain(assignment).get('context', {}).get('a102_task')
    if task is not None:
        if not isinstance(task, dict):
            raise ContractError('a102_structural_evidence_task_contract_mismatch')
        if task != task_context(task.get('name')):
            raise ContractError('a102_structural_evidence_task_contract_mismatch')
        if task['name'] in COMPARATIVE_TASKS:
            from .a102_credit import A102StructuralCredit
            return A102StructuralCredit()
    return finding_progress()
