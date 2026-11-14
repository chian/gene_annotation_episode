from __future__ import annotations

PRIMITIVE_ORDER = ("protein_condition1", "empty_condition1",
                   "protein_condition0", "empty_condition0")

_MEANINGS = ("endpoint", "normalization", "subject_construct", "condition",
             "physical_observation")

_ARRANGEMENTS = ("protein_present", "protein_free_control", "empty_vector_control",
                 "other_specified", "unknown", "conflicting")

_APPLICATIONS = ("matched_condition_control", "shared_reference_assumption",
                 "unknown", "conflicting")

_REUSE = ("distinct_observations", "same_reference_with_stated_invariance",
          "unknown", "conflicting")
