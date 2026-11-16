"""Current Root protein/MACS2 worker selection with original reservation custody.

Saved public and current commands keep their recorded source files. Fresh work
selects the actual private scientific implementations. The shared custodian
retains full command, request, policy, file-pin and process validation.
"""
from pathlib import Path
import sys
from gene_annotation_episode.domain import ContractError

_ROOT = Path(__file__).resolve().parents[3]
_LIBRARY = Path(__file__).resolve().parent
_CURRENT_PACKAGE_FILES = (_ROOT / "episodic_workflow/__init__.py",
    _LIBRARY.parent / "__init__.py", _LIBRARY / "__init__.py")
_CURRENT = "gene_annotation_episode.episodic_workflow.root.library."
_WORKERS = {
    "protein_conservation_native": "muscle_alignment_driver",
    "protein_conservation_result": "protein_conservation_result_worker",
    "protein_phylogeny_iqtree_native": "iqtree_phylogeny_driver",
    "protein_phylogeny_result": "protein_phylogeny_result_worker",
    "macs2_peak_result": "sequence_analysis_worker",
    "somatic_variant_native": "somatic_variant_driver",
    "somatic_variant_result": "somatic_variant_result_worker",
}
OPERATIONS = frozenset(_WORKERS)


def module(operation):
    if operation not in OPERATIONS:
        raise ContractError("molecular_tool_operation_unknown")
    return _CURRENT + _WORKERS[operation]


def recorded_module(operation, selected):
    # The caller owns the complete command equality.
    return module(operation)


def implementation_files(operation):
    if operation in {"protein_conservation_native", "protein_conservation_result", "protein_phylogeny_iqtree_native", "protein_phylogeny_result", "somatic_variant_native", "somatic_variant_result"}:
        import importlib
        from importlib import metadata, util
        from .native_atac_differential_software import _source_closure, _PACKAGES, _OPTIONAL
        # The unchanged scanner follows a package ImportFrom as the package.
        # Include its actual imported member modules explicitly for this owner.
        package_members = {
            "protein_conservation_result_worker": ("gene_annotation_episode.episodic_workflow.root.library.native_artifact_storage", "gene_annotation_episode.episodic_workflow.root.library.phylogeny_calculation_contracts", "gene_annotation_episode.episodic_workflow.root.library.phylogeny_format_contracts", "gene_annotation_episode.episodic_workflow.root.library.protein_conservation_result_contracts",),
            "protein_phylogeny_result_worker": ("gene_annotation_episode.episodic_workflow.root.library.phylogeny_calculation_contracts",),
            "somatic_variant_driver": ("gene_annotation_episode.episodic_workflow.root.library.somatic_variant_contracts", "gene_annotation_episode.episodic_workflow.root.library.vcf_result_measurements",),
            "somatic_variant_result_worker": ("gene_annotation_episode.episodic_workflow.root.library.somatic_variant_contracts", "gene_annotation_episode.episodic_workflow.root.library.vcf_result_measurements",),
        }
        closure = _source_closure(_ROOT.parent,
            [module(operation), *package_members.get(_WORKERS[operation], ())])
        files = [Path(__file__), _ROOT / "molecular_measurement_tools.py", *_CURRENT_PACKAGE_FILES, *closure.values()]
        selected = {**_PACKAGES, 'biopython': 'Bio', 'numpy': 'numpy'}
        for name in selected.values():
            importlib.import_module(name)
        selected.update({name: module for name, module in _OPTIONAL.items() if module in sys.modules})
        for name, import_name in selected.items():
            distribution = metadata.distribution(name)
            root = Path(distribution.locate_file('.')).resolve(strict=True)
            entries = distribution.files
            if not entries:
                raise ContractError('protein_conservation_dependency_files_unavailable')
            installed = []
            for entry in entries:
                # Bytecode and unused console scripts are not imported worker
                # dependencies. Filter them before requiring physical files in
                # the explicitly selected, copied package environment.
                if entry.suffix in {'.pyc', '.pyo'} or '__pycache__' in entry.parts:
                    continue
                path = Path(distribution.locate_file(entry))
                if not path.resolve().is_relative_to(root):
                    continue
                path = path.resolve(strict=True)
                if not path.is_file():
                    raise ContractError('protein_conservation_dependency_file_unavailable')
                installed.append(path)
            specification = util.find_spec(import_name)
            if (specification is None or specification.origin is None
                    or Path(specification.origin).resolve(strict=True) not in installed):
                raise ContractError('protein_conservation_dependency_import_conflict')
            files.extend(installed)
        return list(dict.fromkeys(files))
    if operation != "macs2_peak_result":
        raise ContractError("molecular_tool_operation_unknown")
    modules = ("sequence_analysis_worker.py", "macs2_peak_result_worker.py",
        "macs2_peak_result_contracts.py", "macs2_peak_components.py",
        "atac_differential_inputs.py", "atac_differential_contracts.py",
        "atac_differential_result_contracts.py", "native_macs2_peak_execution.py",
        "native_atac_differential_contracts.py", "native_atac_differential_driver.py")
    return [Path(__file__), _ROOT / "molecular_measurement_tools.py", *_CURRENT_PACKAGE_FILES,
        *(_LIBRARY / name for name in modules)]
