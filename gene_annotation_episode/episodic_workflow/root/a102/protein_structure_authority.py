"""Shared protein receipt-view types and structured operand errors.

These definitions perform no receipt lookup, publication or scientific work.
Actual received authority and retained scientific consistency have separate
owners; both use these detached record types at their explicit boundary.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import TypedDict

from jsonschema import Draft202012Validator, validators

from .domain import ContractError
from .native_protein_structure_contracts import ScientificRequest, Software
from .protein_structure_contracts import (
    FileIdentity, ResultCustody, SavedSheetDescriptor, StructureSequenceDescriptor,
    StructuredIssue, protein_structure_schema_definitions,
)
from .protein_structure_result_views import (
    ProteinFailureReturn, ProteinResultSelector, ProjectionResult,
)


class ProteinFactGroups(TypedDict):
    execution_protein_structure_projections: list[ProjectionResult]
    execution_protein_structure_saved_sheets: list[SavedSheetDescriptor]
    execution_protein_structure_sequences: list[StructureSequenceDescriptor]
    execution_protein_structure_failures: list[ProteinFailureReturn]


class ProteinResultAuthorityRecord(TypedDict):
    custody: ResultCustody
    selector: ProteinResultSelector
    request: ScientificRequest
    software: Software
    native_file: FileIdentity | None
    sequence_file: FileIdentity | None
    residue_map_file: FileIdentity | None
    sheet_file: FileIdentity | None
    original_components_file: FileIdentity | None
    components_file: FileIdentity | None
    facts: ProteinFactGroups


def _finite_number(_checker, value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


_ISSUE_VALIDATOR = validators.extend(
    Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _checker, value: type(value) is int)
    .redefine("number", _finite_number),
)( {"$defs": protein_structure_schema_definitions(), "$ref": "#/$defs/StructuredIssue"} )


class ProteinStructureOperandError(ContractError):
    def __init__(self, problem: StructuredIssue):
        if type(problem) is not dict or not _ISSUE_VALIDATOR.is_valid(problem):
            raise ValueError("invalid_schema")
        self.issue = deepcopy(problem)
        super().__init__(self.issue["code"], detail={"protein_structure_issue": deepcopy(self.issue)})
