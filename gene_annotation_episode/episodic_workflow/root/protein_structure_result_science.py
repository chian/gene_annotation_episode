"""Original retained scientific-byte validation and qualified result reconstruction."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_records import _require, _problem, _unique, _empty_files
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import PROJECTION_SOURCE, SAVED_SOURCE, SEQUENCE_SOURCE
from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_acquisition import decode_protein_structure_json, retained_protein_structure_file
from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_contracts import validate_native_protein_structure_result
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_calculations import validate_recorded_protein_structure_components
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import same
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views import validate_protein_structure_projection_rows
from gene_annotation_episode.execution_contracts import canonical
import hashlib


class ProteinStructureResultScience:
    def _bytes(self, identity, *, role=None):
        try:
            raw = retained_protein_structure_file(self.store, identity).read_bytes()
            if len(raw) != identity["byte_length"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
                raise ValueError("input_digest_mismatch")
            return raw
        except (ValueError, OSError) as error:
            raise ProteinStructureOperandError(_problem(error, role=role)) from error

    def _json(self, identity, *, role=None):
        try:
            return decode_protein_structure_json(self._bytes(identity, role=role), canonical_bytes=True)
        except ValueError as error:
            raise ProteinStructureOperandError(_problem(error, role=role)) from error

    @staticmethod
    def _captured(capture, role):
        rows = [row["observed"] for row in capture["files"]
                if row["declared"]["role"] == role and row["outcome"] == "verified"]
        _require(len(rows) <= 1)
        return deepcopy(rows[0]) if rows else None

    def _original_science(self, body):
        """Read the already qualified worker outputs, without parsing/refitting."""
        worker = body["worker"]
        result = None if worker is None else worker["result"]
        if result is None:
            return None
        operation = result["operation"]
        # 008: a diagnostic C-valid comparison envelope alone is insufficient.
        required = ("native_result_file", "sheet_file", "components_file") if operation == "compare" else ("native_result_file",)
        if any(result[name] is None for name in required):
            return None
        native_file = result["native_result_file"]["file_identity"]
        native = validate_native_protein_structure_result(self._json(native_file, role="native_result"))
        job = body["bundle"]["requested_job"]["native_protein_structure"]
        _require(same(native["request"], job["request"]) and same(native["producer"], job["software"]))
        qualified = _empty_files()
        qualified["native_file"] = deepcopy(native_file)
        if operation == "inspect":
            body["qualified_files"] = qualified
            return {"kind": "inspection", "inventory": native["inventory"]}
        if operation == "extract_sequence":
            body["qualified_files"] = qualified
            sequence = native["sequence"]
            files = {role: self._captured(body["capture"], role)
                     for role in ("sequence", "residue_map", "single_structure")}
            if sequence["sequence_available"] and all(files.values()):
                try:
                    _require(same(files["single_structure"], sequence["selection"]["file_identity"]), "sequence_artifact_mismatch")
                    if (self._bytes(files["sequence"], role="sequence") != sequence["alignment_sequence"].encode("ascii")
                            or self._bytes(files["residue_map"], role="residue_map") != canonical(sequence).encode("utf-8")):
                        raise ValueError("sequence_artifact_mismatch")
                    self._bytes(files["single_structure"], role="single_structure")
                except (ValueError, OSError) as error:
                    body["issues"].append(_problem(error, stage="sequence", field="sequence"))
                else:
                    qualified.update(sequence_file=files["sequence"], residue_map_file=files["residue_map"])
            return {"kind": "extraction", "sequence": sequence, "metadata": native["metadata"], "descriptor": None}
        sheet_file, components_file = [result[name]["file_identity"] for name in ("sheet_file", "components_file")]
        sheet, components = self._json(sheet_file), self._json(components_file)
        _require(same(sheet, native["sheet"]) and same(components, sheet["native_baseline"])
                 and same(components["parameters"], job["request"]["parameters"]))
        validate_recorded_protein_structure_components(sheet, components=components)
        qualified.update(sheet_file=deepcopy(sheet_file), original_components_file=deepcopy(components_file),
                         components_file=deepcopy(components_file))
        body["qualified_files"] = qualified
        body["calculation"] = {"calculation_id": components["calculation_id"],
            "input_numerical_sha256": components["input_numerical_sha256"], "components_file": deepcopy(components_file)}
        return {"kind": "comparison", "sheet": sheet, "components": components}

    def _saved_science(self, body, original, selector):
        result = None if body["worker"] is None else body["worker"]["result"]
        if result is None or result["sheet_file"] is None or result["components_file"] is None:
            return None
        descriptor = selector["saved_sheet"]
        sheet_file = result["sheet_file"]["file_identity"]
        components_file = result["components_file"]["file_identity"]
        _require(same(sheet_file, descriptor["sheet_file"]))
        sheet, components = self._json(sheet_file), self._json(components_file)
        baseline = self._json(descriptor["original_components_file"])
        _require(same(baseline, sheet["native_baseline"])
                 and same(baseline["parameters"], sheet["native_request"])
                 and same(components["parameters"], selector["parameters"]))
        validate_recorded_protein_structure_components(sheet, components=baseline)
        validate_recorded_protein_structure_components(sheet, components=components)
        qualified = _empty_files()
        qualified.update(native_file=deepcopy(original["body"]["qualified_files"]["native_file"]),
            sheet_file=deepcopy(descriptor["sheet_file"]),
            original_components_file=deepcopy(descriptor["original_components_file"]),
            components_file=deepcopy(components_file))
        body["qualified_files"] = qualified
        body["calculation"] = {"calculation_id": components["calculation_id"],
            "input_numerical_sha256": components["input_numerical_sha256"], "components_file": deepcopy(components_file)}
        return {"kind": "comparison", "sheet": sheet, "components": components}

    def _verify_artifacts(self, receipt):
        body, publication = receipt["body"], receipt["publication"]
        files = body["qualified_files"]
        for projection in publication["facts"][PROJECTION_SOURCE]:
            names = ("sheet_file", "components_file") if projection["calculation"] is not None else ("native_file",)
            for name in names:
                _require(files[name] is not None)
                self._bytes(files[name], role="native_result" if name == "native_file" else None)
            if projection["delivery"]["kind"] == "artifact":
                table = self._json(projection["delivery"]["table_file"])
                _require(type(table) is dict and set(table) == {"version", "rows"}
                         and table["version"] == "protein_structure_projection_table_v1", "invalid_schema")
                envelope = {name: deepcopy(projection[name]) for name in ("projection_id", "family", "selection",
                    "coordinate_set", "requested_count", "matched_count", "returned_count", "omitted_count",
                    "state", "issues", "qualifications")}
                envelope.update(version="protein_structure_projection_rows_v1", rows=table["rows"],
                    calculation_id=None if projection["calculation"] is None else projection["calculation"]["calculation_id"])
                validate_protein_structure_projection_rows(envelope)
        for descriptor in publication["facts"][SAVED_SOURCE]:
            self._bytes(descriptor["sheet_file"])
            self._bytes(descriptor["original_components_file"])
        descriptors = list(publication["facts"][SEQUENCE_SOURCE])
        for projection in publication["facts"][PROJECTION_SOURCE]:
            if projection["delivery"]["kind"] == "values":
                descriptors.extend(field["value"] for row in projection["delivery"]["rows"] for field in row["values"]
                    if field["field"] == "descriptor" and field["value"] is not None)
        for descriptor in _unique(descriptors):
            _require(files["native_file"] is not None)
            self._bytes(files["native_file"], role="native_result")
            for name, role in (("sequence_file", "sequence"), ("residue_map_file", "residue_map"), ("structure_file", "single_structure")):
                self._bytes(descriptor[name], role=role)

