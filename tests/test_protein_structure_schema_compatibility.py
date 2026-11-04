"""Default schema compatibility with the authentic pre-action check337 sources."""
import importlib
from pathlib import Path
import sys
from types import ModuleType

import pytest

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode import native_protein_structure_contracts as native
from gene_annotation_episode import protein_structure_contracts as science
from gene_annotation_episode import protein_structure_result_views as views


def legacy_modules():
    # The three preserved source files form one coherent reference cohort.
    # Other unchanged support modules resolve from application source; neither
    # package nor files are modified by this isolated import namespace.
    name = "_protein_structure_legacy_schema_fixture"
    if name not in sys.modules:
        package = ModuleType(name)
        package.__path__ = [
            str(Path(__file__).parent / "fixtures" / "protein_structure_legacy_schema"),
            str(Path(science.__file__).parent),
        ]
        sys.modules[name] = package
    return tuple(importlib.import_module(name + "." + module) for module in (
        "protein_structure_contracts", "native_protein_structure_contracts",
        "protein_structure_result_views"))


@pytest.mark.parametrize("schema_name", [
    "ScientificRequest", "RequestedProteinJob", "NativeProteinBundle", "WorkerInput",
])
def test_default_native_schemas_keep_their_exact_legacy_definitions_and_identity(schema_name):
    _, original, _ = legacy_modules()
    assert canonical(native.protein_structure_execution_schema(schema_name)) == canonical(
        original.protein_structure_execution_schema(schema_name))


@pytest.mark.parametrize("schema_name", ["ProjectionInput", "ProjectionRows", "ProjectionResult"])
def test_default_projection_schemas_keep_their_exact_legacy_definitions_and_identity(schema_name):
    _, _, original = legacy_modules()
    assert canonical(views._schema(schema_name)) == canonical(original._schema(schema_name))


def test_default_scientific_definitions_are_unchanged_by_action_descriptor_support():
    original, _, _ = legacy_modules()
    assert canonical(science.protein_structure_schema_definitions()) == canonical(
        original.protein_structure_schema_definitions())
