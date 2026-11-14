"""Retain exactly the selected protein return, without scientific work.

The result host supplies qualified rows and authenticates their original
operation. A valid custody-shaped value here is not received-use authority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .domain import ContractError
from .execution_contracts import canonical
from .native_protein_structure_acquisition import retained_protein_structure_file
from .protein_structure_contracts import ResultCustody
from .protein_structure_result_views import (
    ProjectionCalculation, ProjectionResult, ProjectionRows,
    validate_protein_structure_projection_result,
    validate_protein_structure_projection_rows,
)


def publish_protein_structure_projection(
    store, *, rows: ProjectionRows, custody: ResultCustody,
    calculation: ProjectionCalculation | None,
) -> ProjectionResult:
    """Copy values, or retain only the explicitly selected table's exact bytes.

    Native parsing, numerical calculations, component-file qualification and
    original receipt authentication belong to the supplying result host.
    Historical readers consume its recorded publication, not this writer.
    """
    selected = validate_protein_structure_projection_rows(rows)
    if calculation is not None and type(calculation) is not dict:
        raise ValueError("invalid_schema")
    if selected["calculation_id"] != (None if calculation is None else calculation.get("calculation_id")):
        raise ValueError("conflicting_identity")

    result = {key: value for key, value in selected.items()
              if key not in {"rows", "calculation_id"}}
    result.update(version="protein_structure_projection_v1",
                  custody=deepcopy(custody), calculation=deepcopy(calculation))
    data = None
    if selected["selection"]["delivery_kind"] == "values":
        result["delivery"] = {"kind": "values", "rows": selected["rows"]}
    else:
        data = canonical({"version": "protein_structure_projection_table_v1",
                          "rows": selected["rows"]}).encode("utf-8")
        sha256 = hashlib.sha256(data).hexdigest()
        table = {"artifact_ref": "artifact_" + sha256, "sha256": sha256,
                 "byte_length": len(data), "format": "protein_structure_projection_table_v1"}
        result["delivery"] = {"kind": "artifact", "table_file": table,
                              "row_count": selected["returned_count"],
                              "allowed_use": "read_exact_selected_table"}

    # Reject malformed custody, counts and relationships before any mutation.
    result = validate_protein_structure_projection_result(result)
    if data is not None:
        table = result["delivery"]["table_file"]
        with store.transaction():
            try:
                store.get(table["artifact_ref"])
            except ContractError as error:
                if str(error) != "unknown_reference":
                    raise ValueError("invalid_schema") from error
                reference = store.artifact(data, media_type="application/json")
            else:
                # Previously retained data is read-only here: missing bytes
                # must not be silently recreated during a replay.
                reference = table["artifact_ref"]
            if reference != table["artifact_ref"]:
                raise ValueError("input_digest_mismatch")
            # Store's content-addressed INSERT OR IGNORE is also a replay path.
            # Check existing metadata and actual bytes, not only the filename.
            retained_protein_structure_file(store, table)
    return result
