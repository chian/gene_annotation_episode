"""Original controlled request helpers for a publication-input boundary only."""
from .bvbrc_phylogeny_saved_fixture import selector


def output_target(query):
    query["workspace_targets"].append({"target_id": "output", "path": query["parameters"]["output_path"],
        "type": "folder", "purpose": "output_parent", "input_binding_id": None, "metadata": {},
        "allow_overwrite": False, "allow_create_parents": True})
    return {"kind": "original_target", "target_id": "output"}


def download_args(obj, capability):
    return {"object": obj, "capability": capability, "byte_range": None, "max_bytes": 1048576, "requirement_ids": ["native"],
        "role": "native_output", "declared_format": selector()["requirements"][0]["declared_format"]}
