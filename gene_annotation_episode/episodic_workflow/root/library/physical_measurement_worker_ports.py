"""Current three-operation scientific selection through original process custody.

Original public commands and their retained pins stay original. These ports
only choose the actual private worker and explicit current source operands.
They neither change a scientific setting nor create or monitor a process.
"""
from pathlib import Path
from gene_annotation_episode.domain import ContractError

_PACKAGE = Path(__file__).resolve().parents[3]
_LIBRARY = Path(__file__).resolve().parent
_CURRENT_PACKAGE_FILES = (_PACKAGE / "episodic_workflow/__init__.py",
    _LIBRARY.parent / "__init__.py", _LIBRARY / "__init__.py")
OPERATIONS = frozenset({"itc_binding", "liftover_point", "circular_dichroism"})


def module(operation):
    if operation not in OPERATIONS:
        raise ContractError("molecular_tool_operation_unknown")
    return "gene_annotation_episode.episodic_workflow.root.library.physical_measurement_worker"


def recorded_module(operation, selected):
    # Full command/request/policy/source checks remain in the custodian.
    return module(operation)


def implementation_files(operation):
    # Original finite scientific groups, mapped to their actual defining files.
    # The split ITC tools/custody and current worker/selector are real additions.
    groups = {
        "itc_binding": ("itc_tools.py", "itc_binding_contracts.py", "itc_binding_measurements.py",
            "itc_binding_fit.py", "bivariate_covariance.py", "molecular_action_custody.py",
            "molecular_publication_custody.py"),
        "liftover_point": ("liftover_contracts.py", "liftover_measurements.py"),
        "circular_dichroism": ("circular_dichroism_contracts.py", "circular_dichroism_measurements.py",
            "circular_dichroism_tools.py", "molecular_sequence_input_contracts.py"),
    }
    if operation not in groups:
        raise ContractError("molecular_tool_operation_unknown")
    files = [Path(__file__), _PACKAGE / "molecular_measurement_tools.py", *_CURRENT_PACKAGE_FILES,
        _LIBRARY / "physical_measurement_worker.py", *(_LIBRARY / name for name in groups[operation])]
    distributions = {"liftover_point": (("pyliftover", "pyliftover"),)}
    for distribution_name, import_name in distributions.get(operation, ()):
        from importlib import metadata, util
        from gene_annotation_episode.acquisition import AcquisitionError
        try:
            distribution = metadata.distribution(distribution_name)
            entries = distribution.files
            if not entries:
                raise ValueError(distribution_name + "_distribution_files_unavailable")
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
