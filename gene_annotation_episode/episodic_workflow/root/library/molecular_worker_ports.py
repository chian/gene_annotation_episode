"""Root molecular operation source selection at the existing owned-worker boundary.

The shared process custodian still owns reservation, launch, observation and
recovery. These ports select actual scientific definers for four operations.
Historical public reservations and caller-selected native deployments retain
their original module and source records.
"""
from pathlib import Path
import hashlib

from gene_annotation_episode.domain import ContractError


OPERATIONS = frozenset(("protein_disorder", "arsenic_speciation",
    "protease_kinetics_native", "protease_kinetics_saved"))
_ROOT = Path(__file__).resolve().parents[3]
_LIBRARY = Path(__file__).resolve().parent
_CURRENT = "gene_annotation_episode.episodic_workflow.root.library."
_LEGACY = "gene_annotation_episode."


def validation_owners():
    from . import molecular_sequence_driver as driver
    from . import molecular_sequence_native as native
    from .protease_kinetics_measurements import _native_request
    return driver, native, _native_request


def module(operation, *, current=True):
    if operation not in OPERATIONS:
        raise ContractError("molecular_tool_operation_unknown")
    name = "molecular_sequence_driver" if operation.startswith("protease_kinetics_") else "sequence_worker"
    return (_CURRENT if current else _LEGACY) + name


def recorded_module(operation, selected):
    """Recognize current argv; the original full command equality remains caller-owned.

    Unrecognized/malformed argv retains the old expected command, hence the
    original validator still rejects it with its original error and ordering.
    No saved source file is replaced or compared to today's implementation here.
    """
    command = selected.get("command") if type(selected) is dict else None
    index = 3 if operation.startswith("protease_kinetics_") else 2
    if type(command) is list and len(command) > index and command[index] == module(operation):
        return module(operation)
    return module(operation, current=False)


def implementation_files(operation):
    """The actual relocated counterparts of the original scientific operands.

    This preserves the original finite inventory rather than claiming all
    dynamically reachable imports. New direct custody and validation owners are
    included explicitly; unrelated operations keep their original inventory.
    """
    common = ("molecular_action_custody.py", "molecular_publication_custody.py",
        "reference_edit_outcome_tools.py", "molecular_sequence_result_contracts.py",
        "native_atac_differential_driver.py", "alignment_site_native.py")
    groups = {
        "protein_disorder": ("sequence_worker.py", "protein_disorder_tools.py",
            "protein_disorder_measurements.py", "protein_disorder_result_contracts.py",
            "sequence_composition_grader.py", "sequence_mapping.py"),
        "arsenic_speciation": ("sequence_worker.py", "calibrated_signal_contracts.py",
            "calibrated_signal_sheet.py", "calibrated_signal_calculations.py",
            "arsenic_speciation_tools.py", "arsenic_speciation_result_contracts.py",
            "molecular_sequence_input_contracts.py"),
        "protease_kinetics_native": ("molecular_sequence_driver.py", "molecular_sequence_native.py",
            "protease_kinetics_measurements.py", "bivariate_covariance.py", "orf_measurements.py",
            "primer_placement_measurements.py", "glycosylation_measurements.py",
            "sequence_translation_grader.py", "sequence_mapping.py", "sequence_extraction_grader.py",
            "sequence_composition_grader.py", "biopython_pairwise_grader.py"),
    }
    groups["protease_kinetics_saved"] = groups["protease_kinetics_native"]
    if operation not in groups:
        raise ContractError("molecular_tool_operation_unknown")
    files = [Path(__file__), *(_LIBRARY / name for name in groups[operation])]
    if not operation.startswith("protease_kinetics_"):
        files.extend(_LIBRARY / name for name in common)
        files.extend(_ROOT / name for name in ("molecular_measurement_tools.py", "acquisition.py",
            "boundary_validation.py", "domain.py", "execution_contracts.py", "native_file_capture.py"))
    else:
        # The moved native implementation imports its genuine historical error
        # object; that exact original type provider belongs to the supplied set.
        files.append(_ROOT / "molecular_sequence_native.py")
    return list(dict.fromkeys(files))


def expected_paths(deployment, files):
    package_parent = _ROOT.parent
    return {str(Path(root) / path.relative_to(package_parent)): path
        for root in deployment["import_roots"] for path in files}


def native_selection(deployment, index, files):
    """Prefer a complete explicitly supplied current driver; otherwise preserve legacy.

    The unchanged caller checks every chosen source byte. This does not install
    or infer a replacement deployment. A complete legacy set remains admissible
    even when it carries additional unrelated files, as in the original code.
    """
    expected = expected_paths(deployment, files)
    complete = all(len([pin for name, pin in index.items()
        if name in expected and expected[name] == path
        and pin["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()]) == 1 for path in files)
    if complete:
        return module("protease_kinetics_native"), files, expected
    from gene_annotation_episode.molecular_measurement_tools import _molecular_implementation_files
    old = _molecular_implementation_files("protease_kinetics_native")
    return module("protease_kinetics_native", current=False), old, {
        str(Path(root) / "gene_annotation_episode" / path.name): path
        for root in deployment["import_roots"] for path in old}
