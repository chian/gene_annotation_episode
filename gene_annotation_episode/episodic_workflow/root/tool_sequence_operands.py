"""Original substantive ordinary-tool methods: tool_sequence_operands."""
from __future__ import annotations
import hashlib
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.library.sequence_views import view_sequence
from gene_annotation_episode import library_targets as libraries
from gene_annotation_episode import materials_packing as packing

class ToolSequenceOperands:
    def _check_target(self, reference: str, scope: dict | None, *, footprint: list[dict] | None = None) -> dict:
        row = self.store.get(reference)
        footprint = self.store.coverage(reference) if footprint is None else footprint
        normalized = self.store.validate_scope(scope)
        allowed = set(normalized["subject_refs"])
        if not footprint or any(item["target_ref"] not in allowed for item in footprint):
            raise ContractError("subject_outside_assigned_scope")
        if not self.store.scope_covers(footprint, normalized):
            raise ContractError("requested_measurement_outside_assigned_segments_or_members"
                if any("member_ref" in span for span in footprint)
                else "requested_measurement_outside_assigned_segments")
        return row

    def _sequence(self, reference: str, *, molecule_model: str | None = None) -> str:
        row = self.store.get(reference)
        if row.get("record_type") == "read_subject":
            member = self.store.get(row["member_ref"])
            return packing.component_window(self.store, member, "sequence", 0, row["length"]).decode("ascii")
        if libraries.is_library(row):
            raise ContractError("library_is_not_a_sequence_operand")
        if row.get("sequence_ref"):
            return self.store.get_artifact(row["sequence_ref"]).decode("ascii")
        if row.get("record_type") == "feature":
            parent = self._sequence(row["subject_ref"], molecule_model=molecule_model)
            sequence = "".join(parent[item["start"]:item["end"]] for item in row["segments"])
            if row["strand"] == "-":
                known_model = self.store.subject_molecule(row["subject_ref"])
                model = known_model if known_model != "unspecified" else molecule_model
                try:
                    return view_sequence(sequence, molecule=model, orientation="reverse_complement")["sequence"]
                except ValueError as error:
                    raise ContractError(str(error)) from error
            return sequence
        raise ContractError("referenced_record_has_no_sequence")

    def _check_sequence_operand(self, reference: str, scope: dict | None,
                                *, footprint: list[dict] | None = None) -> dict:
        """Resolve scientific sequence material without turning it into a target.

        Original-input work retains its assigned ownership bounds. Registered
        external evidence and its derivatives have no input credit footprint;
        their absence of one is not a prohibition on investigating the source.
        """
        row = self.store.get(reference)
        if row["record_type"] not in {"input", "feature", "product", "reference", "read_subject"}:
            raise ContractError("sequence_operand_required")
        self.store.subject_length(reference)
        self.store.validate_scope(scope)
        if self.store.roots(reference):
            return self._check_target(reference, scope, footprint=footprint)
        return row

    def _prepare_molecular_sequence_operand(self, operation: str, subject_ref: str, *, scope) -> dict:
        """Freeze an admitted operand using the existing sequence and scope owners.

        The ordinary-operation caller authenticates its actual selected action.
        This private snapshot grants no references and performs no scientific analysis.
        """
        from copy import deepcopy
        from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import ordinary_molecular_sequence_profile
        profile = ordinary_molecular_sequence_profile(operation)
        with self.store.read_snapshot():
            subject = deepcopy(self._check_sequence_operand(subject_ref, scope))
            sequence = self._sequence(subject_ref, molecule_model=profile["molecule_model"])
            footprint = self.store.coverage(subject_ref)
            mapping_failure = None
            try:
                mapping = self.store.sequence_mapping(subject_ref)
            except ContractError as error:
                if str(error) != 'subregion_mapping_unavailable':
                    raise
                mapping = None
                mapping_failure = {'code': 'subregion_mapping_unavailable'}
            associations = {key: deepcopy(value) for key, value in subject.items()
                if key.endswith(('_ref', '_refs'))}
        raw = sequence.encode('ascii')
        reference = self.store.artifact(raw, 'text/plain')
        if subject.get('sequence_ref') and reference != subject['sequence_ref']:
            prefix = ("orf" if operation == "annotate_open_reading_frames" else
                "primer_placement" if operation == "align_sequences" else
                "o_glycosylation" if operation == "predict_o_glycosylation_hotspots" else "n_glycosylation")
            raise ContractError(prefix + '_sequence_file_identity_conflict')
        return {'version': profile["operand_version"], 'subject': subject,
            'sequence': sequence, 'parent_mapping': mapping, 'mapping_failure': mapping_failure,
            'input_file': {'artifact_ref': reference, 'sha256': hashlib.sha256(raw).hexdigest(),
                'size_bytes': len(raw), 'format': 'ascii_sequence'},
            'associations': associations, 'footprint': footprint}

    def _prepare_orf_sequence_operand(self, subject_ref: str, *, scope) -> dict:
        """Freeze the ORF operand record."""
        return self._prepare_molecular_sequence_operand("annotate_open_reading_frames", subject_ref, scope=scope)

