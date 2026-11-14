"""Current HOMER result and TF worker selection with original saved custody.

These three operation ports select scientific implementations, not process
policy. Existing shared reservation, input checks, errors and saved file pins
remain authoritative. Caller-provided HOMER native deployments are separate.
"""
from pathlib import Path
from gene_annotation_episode.domain import ContractError

_ROOT = Path(__file__).resolve().parents[3]
_LIBRARY = Path(__file__).resolve().parent
_CURRENT_PACKAGE_FILES = (_ROOT / "episodic_workflow/__init__.py",
    _LIBRARY.parent / "__init__.py", _LIBRARY / "__init__.py")
_CURRENT = "gene_annotation_episode.episodic_workflow.root.library."
_LEGACY = "gene_annotation_episode."
_WORKERS = {"homer_motif_result": "native_homer_worker",
    "tf_binding_native": "tf_binding_driver", "tf_binding_result": "tf_binding_result_worker"}
OPERATIONS = frozenset(_WORKERS)


def module(operation, *, current=True):
    if operation not in OPERATIONS:
        raise ContractError("molecular_tool_operation_unknown")
    return (_CURRENT if current else _LEGACY) + _WORKERS[operation]


def recorded_module(operation, selected):
    # The caller still requires the complete original argv, metadata and pins.
    # Unknown/malformed commands retain the old expected value and its error.
    command = selected.get("command") if type(selected) is dict else None
    if type(command) is list and len(command) > 2 and command[2] == module(operation):
        return module(operation)
    return module(operation, current=False)


def implementation_files(operation):
    # The original explicit inventories, mapped to their actual defining owners.
    # Split storage primitives and this new selector are explicit new operands;
    # this does not claim a transitive import census or replace saved inventories.
    storage = ("native_artifact_storage.py", "retained_file_read.py", "retained_file_pin.py", "record_serialization.py")
    groups = {
        "homer_motif_result": ("native_homer_worker.py", "homer_motif_contracts.py",
            "homer_motif_measurements.py", "homer_motif_result_contracts.py",
            "bvbrc_alignment_values.py", "phylogeny_calculation_contracts.py",
            "native_flux_balance_contracts.py", "native_homer_execution.py"),
        "tf_binding_native": ("tf_binding_driver.py", "tf_binding_measurements.py",
            "blast_fasta_record_identity.py", "bvbrc_alignment_values.py", "phylogeny_calculation_contracts.py"),
        "tf_binding_result": ("tf_binding_result_worker.py", "tf_binding_measurements.py",
            "blast_fasta_record_identity.py", "bvbrc_alignment_values.py", "phylogeny_calculation_contracts.py"),
    }
    if operation not in groups:
        raise ContractError("molecular_tool_operation_unknown")
    files = [Path(__file__), _ROOT / "molecular_measurement_tools.py", *_CURRENT_PACKAGE_FILES,
        *(_LIBRARY / name for name in groups[operation]), *(_LIBRARY / name for name in storage),
        _ROOT / "domain.py"]
    if operation == "homer_motif_result":
        files.extend(_ROOT / name for name in ("native_file_capture.py", "native_file_identity.py", "materials.py", "execution_contracts.py"))
    elif operation == "tf_binding_result":
        files.extend(_ROOT / name for name in ("native_file_capture.py", "native_file_identity.py"))
    distributions = {
        "tf_binding_native": (("biopython", "Bio"), ("numpy", "numpy")),
        "tf_binding_result": (("biopython", "Bio"), ("numpy", "numpy")),
    }
    for distribution_name, import_name in distributions.get(operation, ()):
        from importlib import metadata, util
        from gene_annotation_episode.acquisition import AcquisitionError
        try:
            distribution = metadata.distribution(distribution_name)
            entries = distribution.files
            if not entries:
                raise ValueError(distribution_name + "_distribution_files_unavailable")
            if operation in {"tf_binding_native", "tf_binding_result"}:
                distribution_root = Path(distribution.locate_file(".")).resolve(strict=True)
                # Imported package code and native libraries belong to this
                # selection. Unused console scripts outside its import root do
                # not become prerequisites of either TF worker.
                entries = [entry for entry in entries
                    if Path(distribution.locate_file(entry)).resolve().is_relative_to(distribution_root)]
            installed = [Path(distribution.locate_file(entry)).resolve(strict=True)
                for entry in entries if entry.suffix != ".pyc" and "__pycache__" not in entry.parts]
            specification = util.find_spec(import_name)
            if (specification is None or specification.origin is None
                    or Path(specification.origin).resolve(strict=True) not in installed
                    or any(not path.is_file() for path in installed)):
                raise ValueError(distribution_name + "_distribution_import_conflict")
        except (metadata.PackageNotFoundError, OSError, ValueError) as error:
            reason = ("distribution_metadata_unavailable" if isinstance(error, metadata.PackageNotFoundError)
                else "distribution_file_unavailable" if isinstance(error, OSError)
                else "distribution_import_or_files_conflict")
            raise AcquisitionError(distribution_name + "_not_installed", phase="local_preflight",
                operational={"software": distribution_name, "reason": reason}) from error
        files.extend(installed)
    return list(dict.fromkeys(files))
