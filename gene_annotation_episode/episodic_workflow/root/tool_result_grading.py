"""Ordinary-tool methods: tool_result_grading."""
from __future__ import annotations
from gene_annotation_episode import materials_packing as packing
from .tool_values import number
from .tool_values import measurements

class ToolResultGrading:
    def _grade_supplied_result(self, grader, *args, **kwargs):
        """Preserve native evidence when a grading input contract rejects it."""
        try:
            return grader(*args, **kwargs)
        except ValueError as error:
            failure = {"code": str(error), "category": "grading_input"}
            failures = self._grading_failures.get()
            if failures is not None:
                failures.append(failure)
            return {"sheet": None, "scores": None, "failure": failure}

    @staticmethod
    def _grading_values(scores, names):
        # Missing components stay absent from this numeric-only observation
        # projection. Their exact unavailable reasons remain in the full sheet.
        return measurements(**{name: number(scores[name]) for name in names
            if type(scores.get(name)) in (int, float)})

    def _composition_grading(self, subject, sequence):
        from gene_annotation_episode.episodic_workflow.root.library.sequence_composition_grader import grade_sequence_composition
        member_ref = (subject.get("member_ref") if subject["record_type"] == "read_subject"
            else subject.get("source_record", {}).get("member_ref")
            if subject["record_type"] == "input" else None)
        quality, encoding = None, None
        if member_ref:
            member = self.store.get(member_ref)
            encoding = member.get("quality_encoding")
            if packing.component_info(self.store, member, "quality") is not None:
                quality = b"".join(packing.component_chunks(self.store, member, "quality")).decode("ascii")
        return self._grade_supplied_result(grade_sequence_composition, sequence,
            molecule=self.store.subject_molecule(subject["id"]),
            quality=quality, quality_encoding=encoding)

    @classmethod
    def _composition_values(cls, grading):
        return cls._grading_values(grading.get("scores") or {}, (
            "unambiguous_nucleotide_count", "ambiguous_symbol_count", "ambiguity_fraction",
            "gc_count", "gc_denominator", "quality_observation_count", "mean_phred",
            "mean_error_probability", "expected_error_count"))

