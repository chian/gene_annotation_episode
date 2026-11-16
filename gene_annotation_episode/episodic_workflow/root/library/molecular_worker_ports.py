"""Root molecular operation source selection at the existing owned-worker boundary.

The shared process custodian still owns reservation, launch, observation and
recovery. These ports select actual scientific definers for four operations.
"""
from pathlib import Path

from gene_annotation_episode.domain import ContractError


OPERATIONS = frozenset(("protein_disorder", "arsenic_speciation",
    "protease_kinetics_native", "protease_kinetics_saved"))
_ROOT = Path(__file__).resolve().parents[3]
_LIBRARY = Path(__file__).resolve().parent
_CURRENT = "gene_annotation_episode.episodic_workflow.root.library."


def validation_owners():
    from . import molecular_sequence_driver as driver
    from . import molecular_sequence_native as native
    from .protease_kinetics_measurements import _native_request
    return driver, native, _native_request


def module(operation):
    if operation not in OPERATIONS:
        raise ContractError("molecular_tool_operation_unknown")
    name = "molecular_sequence_driver" if operation.startswith("protease_kinetics_") else "sequence_worker"
    return _CURRENT + name


def recorded_module(operation, selected):
    """The one worker module; the caller owns the full command equality."""
    return module(operation)


def implementation_files(operation):
    """The finite source inventory of each operation, not every reachable import."""
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
        # The native implementation imports its error object from this provider.
        files.append(_ROOT / "molecular_sequence_native.py")
    return list(dict.fromkeys(files))


def expected_paths(deployment, files):
    package_parent = _ROOT.parent
    return {str(Path(root) / path.relative_to(package_parent)): path
        for root in deployment["import_roots"] for path in files}


def native_selection(deployment, index, files):
    """Bind the explicitly supplied driver; the caller checks every chosen source byte."""
    return module("protease_kinetics_native"), files, expected_paths(deployment, files)
