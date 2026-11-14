"""Explicit current Root optical custody and exact legacy receipt verification.

Original release hashes identify reconstructed original source, not current files.
"""
import hashlib
import json
from pathlib import Path

_PINNED = {"literature_optical_inputs.py": "6e956a39196800d2fe2e4e841a913f40ae4f2d1c44c1fd54fc6abdc6afd6b474",
    "literature_optical_calculations.py": "1242c0e58e83a1ef4e4e8f25bbf94737b33dc706e61794c6ff98b87ce3c5740e",
    "literature_optical_validation.py": "4340cce4a7a659d167b15fcb707b646bd13f8d213e36e0957a454cc02eb54425"}



_SPEC = json.loads("{\"current\":{\"literature_optical_calculations.py\":{\"relative_target\":\"library/literature_optical_calculations.py\",\"sha256\":\"97e204b2c013f818859ce440966588bfc66554484863fd57fab2569cdc326582\"},\"literature_optical_inputs.py\":{\"relative_target\":\"literature_optical_inputs.py\",\"sha256\":\"dab9ad446c3124f588384351c0fbb0e3a3c85bb3a092135f1f84507e38d17b93\"},\"literature_optical_validation.py\":{\"relative_target\":\"library/literature_optical_validation.py\",\"sha256\":\"2942cb69647282cf7b24e361c2852798559365da441942ec952fbfb22a5398d6\"}},\"inverse\":{\"literature_optical_calculations.py\":[{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_experimental_contracts import ExperimentalContractError\\n\",\"before\":\"from .literature_experimental_contracts import ExperimentalContractError\\n\",\"kind\":\"actual_defining_owner_import\",\"offset\":522}],\"literature_optical_inputs.py\":[{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_optical_return_contracts import INTERPRETATIONS\\n\\n\",\"before\":\"INTERPRETATIONS = {\\n    \\\"signal_kind\\\": (\\\"absorbance_slope\\\", \\\"absorbance_difference\\\", \\\"static_absorbance\\\", \\\"unknown\\\"),\\n    \\\"relation\\\": (\\\"applicable_extinction_relation\\\", \\\"not_applicable\\\", \\\"unknown\\\", \\\"conflicting\\\"),\\n    \\\"blank_role\\\": (\\\"matched_no_reaction_background\\\", \\\"condition_reference\\\", \\\"component_omission\\\", \\\"unknown\\\", \\\"conflicting\\\"),\\n    \\\"same_endpoint\\\": (\\\"same\\\", \\\"different\\\", \\\"unknown\\\"),\\n    \\\"matched_window\\\": (\\\"same\\\", \\\"different\\\", \\\"unknown\\\"),\\n    \\\"rate_window\\\": (\\\"source_supported_rate_interval\\\", \\\"interval_mean_only\\\", \\\"static_only\\\", \\\"unknown\\\"),\\n}\\n\",\"kind\":\"new_pure_partition\",\"offset\":1297},{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_optical_return_contracts import LITERAL_FIELDS\\n\\n\",\"before\":\"LITERAL_FIELDS = (\\\"molecule\\\", \\\"construct\\\", \\\"preparation\\\", \\\"condition\\\", \\\"measured_entity\\\")\\n\",\"kind\":\"new_pure_partition\",\"offset\":1024},{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_optical_return_contracts import PRIMITIVE_ORDER\\n\\n\",\"before\":\"PRIMITIVE_ORDER = (\\\"sample_slope\\\", \\\"blank_slope\\\", \\\"epsilon\\\", \\\"path_length\\\")\\n\",\"kind\":\"new_pure_partition\",\"offset\":870},{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_optical_return_contracts import QUALIFICATIONS\\n\\n\",\"before\":\"QUALIFICATIONS = (\\\"reported_point\\\", \\\"source_qualified_approximate\\\", \\\"unknown\\\", \\\"conflicting\\\")\\n\",\"kind\":\"new_pure_partition\",\"offset\":1276},{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_optical_return_contracts import SOURCE_KINDS\\n\\n\",\"before\":\"SOURCE_KINDS = (\\\"primary_source\\\", \\\"retained_extraction\\\", \\\"synthetic_fixture\\\")\\n\",\"kind\":\"new_pure_partition\",\"offset\":990},{\"after\":\"from gene_annotation_episode.domain import REF, ContractError, identity, obj, validate_schema\\n\",\"before\":\"from .domain import REF, ContractError, identity, obj, validate_schema\\n\",\"kind\":\"actual_defining_owner_import\",\"offset\":533},{\"after\":\"from gene_annotation_episode.episodic_workflow.root.literature_assay_inputs import _Sources, _json_source, _nullable\\nfrom gene_annotation_episode.episodic_workflow.root.library.literature_rate_unit_witness_schema import _witness_schema\\n\",\"before\":\"from .literature_assay_inputs import _Sources, _json_source, _nullable, _witness_schema\\n\",\"kind\":\"actual_defining_owner_import\",\"offset\":627},{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_experimental_contracts import ExperimentalContractError\\n\",\"before\":\"from .literature_experimental_contracts import ExperimentalContractError\\n\",\"kind\":\"actual_defining_owner_import\",\"offset\":863},{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_rate_native_inputs import _number, _field_contexts\\n\",\"before\":\"from .literature_rate_native_inputs import _number, _field_contexts\\n\",\"kind\":\"actual_defining_owner_import\",\"offset\":990}],\"literature_optical_validation.py\":[{\"after\":\"from gene_annotation_episode.domain import identity\\n\",\"before\":\"from .domain import identity\\n\",\"kind\":\"actual_defining_owner_import\",\"offset\":624},{\"after\":\"from gene_annotation_episode.episodic_workflow.root.library.literature_experimental_contracts import ExperimentalContractError\\n\",\"before\":\"from .literature_experimental_contracts import ExperimentalContractError\\n\",\"kind\":\"actual_defining_owner_import\",\"offset\":676}]},\"selected_owner\":{\"relative_target\":\"library/literature_optical_return_contracts.py\",\"sha256\":\"399e73d2b7bd6eade6ad96fe6717be3c853f251a1d238629793d42bc8d88d051\"}}")

def current_dependencies(fail):
    root = Path(__file__).resolve().parent.parent
    current = {}
    originals = {}
    for name, selected in _SPEC["current"].items():
        source = (root / selected["relative_target"]).read_bytes()
        current[name] = hashlib.sha256(source).hexdigest()
        if current[name] != selected["sha256"]:
            fail("implementation_dependency_mismatch")
        for edit in reversed(_SPEC["inverse"][name]):
            offset = edit["offset"]
            after = edit["after"].encode("utf-8")
            before = edit["before"].encode("utf-8")
            if source[offset:offset + len(after)] != after:
                fail("implementation_dependency_mismatch")
            source = source[:offset] + before + source[offset + len(after):]
        originals[name] = hashlib.sha256(source).hexdigest()
        if originals[name] != _PINNED[name]:
            fail("implementation_dependency_mismatch")
    selected = _SPEC["selected_owner"]
    owner_hash = hashlib.sha256((root / selected["relative_target"]).read_bytes()).hexdigest()
    if owner_hash != selected["sha256"]:
        fail("implementation_dependency_mismatch")
    return {"version": "root_optical_dependency_receipt_v1",
            "current_sha256": current,
            "selected_owner_sha256": {selected["relative_target"]: owner_hash},
            "original_sha256": originals,
            "validation_version": "a105_optical_saved_validation_v1"}


def saved_dependencies_valid(saved, fail):
    current = current_dependencies(fail)
    legacy = {"sha256": dict(_PINNED), "validation_version": current["validation_version"]}
    return saved == current or saved == legacy
