"""Frozen, exact registered BLAST utility schemas for unchanged saved forms.

Extracted from sealed check096 and check101 source snapshots by bounded529
check111c_historical652. The recorded source pins are provenance, never runtime
imports or executable source. Only complete registered schemas are accepted;
current result views still own validation of values and their relationships.

Immutable serialized documents prevent callers from modifying registration.
Each public accessor returns detached trees. No saved request is rewritten.
"""
from __future__ import annotations

import json


_SOURCE_PROVENANCE_JSON = r'''
{
  "check096_blast_utility_full_workflow": {
    "schemas_sha256": "14ca7759d577dc7f2d3947fd2e11ac90741b3ef5ddebb78c2fcc0e3a21cab99e",
    "source_files_sha256": {
      "__init__.py": "b08e7be9692cc6095dcc1aef62048ed979de4c0ffe5ba610db2f2b0ffc395d5e",
      "blast_program_context.py": "145df024f480d6a1ffb6c01d2fca27a15fc29c0e271d408c11c5ba21c40888ce",
      "blast_utility_contracts.py": "d52b3fc090e3a30c280208cdce1912716e022a81ad17f8dd89aefea828e4ad0d",
      "blast_utility_result_views.py": "8af8bcad56a21c572c6d07627220dfbcc3ce1491c4b0cc357795e9ecf2285cab",
      "domain.py": "2c56c927ebc1cc4430a28733f9708c500b9eb8944a83f4c32ad228ac6cb9cbff",
      "native_blast_standard_database_contracts.py": "7db4d438fc0f4697688fc91b68b46b99094389a496380d887d07446af6392455"
    }
  },
  "check101_mask_conversion_workflow": {
    "schemas_sha256": "2d79aa19613ffd5688618ca2dcb25086031628b5a49703826eb16ea1a0b6c6af",
    "source_files_sha256": {
      "__init__.py": "b08e7be9692cc6095dcc1aef62048ed979de4c0ffe5ba610db2f2b0ffc395d5e",
      "blast_program_context.py": "145df024f480d6a1ffb6c01d2fca27a15fc29c0e271d408c11c5ba21c40888ce",
      "blast_utility_contracts.py": "f02195dccbeba56b8e5b02b2f5766e96233c4f74964a74b2d43dd398a5548abf",
      "blast_utility_result_views.py": "8af8bcad56a21c572c6d07627220dfbcc3ce1491c4b0cc357795e9ecf2285cab",
      "domain.py": "2c56c927ebc1cc4430a28733f9708c500b9eb8944a83f4c32ad228ac6cb9cbff",
      "native_blast_standard_database_contracts.py": "7db4d438fc0f4697688fc91b68b46b99094389a496380d887d07446af6392455"
    }
  }
}
'''


_HISTORICAL_REGISTRY_JSON = r'''
{
  "execution.blast_utility_artifacts": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "artifact_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "artifact"
          },
          "completeness": {
            "enum": [
              "complete",
              "partial",
              "unknown"
            ]
          },
          "direction": {
            "enum": [
              "input",
              "output"
            ]
          },
          "native_format": {
            "enum": [
              "fasta",
              "blastdbcmd_tabular_v1",
              "blastdb_info_text",
              "blastdb_metadata_json",
              "blastdbcheck_text",
              "blastdb_binary",
              "json",
              "text",
              "maskinfo_xml",
              "maskinfo_asn1_text",
              "unknown"
            ]
          },
          "native_path": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "occurrence_id": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "native_blast_utility_occurrence"
          },
          "ordinal": {
            "minimum": 0,
            "type": "integer"
          },
          "role": {
            "enum": [
              "sequence_input",
              "database_file",
              "database_metadata",
              "extracted_sequences",
              "database_manifest",
              "taxid_map",
              "mask_input",
              "stdout",
              "stderr",
              "diagnostics",
              "preparation_receipt",
              "input_manifest",
              "offline_configuration"
            ]
          },
          "sha256": {
            "pattern": "[0-9a-f]{64}",
            "type": "string"
          },
          "size_bytes": {
            "minimum": 0,
            "type": "integer"
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "occurrence_id",
          "direction",
          "role",
          "ordinal",
          "artifact_ref",
          "sha256",
          "size_bytes",
          "native_format",
          "completeness",
          "native_path"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_artifacts"
    }
  ],
  "execution.blast_utility_checks": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "evidence_occurrence_ids": {
            "items": {
              "minLength": 1,
              "type": "string"
            },
            "type": "array",
            "uniqueItems": true
          },
          "method": {
            "enum": [
              "identity_digest",
              "family_inventory",
              "native_format_parser",
              "explicit_reference_join",
              "selected_record_match",
              "sequence_length_agreement",
              "native_full_check",
              "native_sample_check",
              "native_execution_outcome"
            ]
          },
          "name": {
            "enum": [
              "custody",
              "syntax",
              "identity",
              "selection",
              "sequence_length",
              "sequence_symbols",
              "database_inventory",
              "database_metadata",
              "native_integrity",
              "native_execution"
            ]
          },
          "reason": {
            "anyOf": [
              {
                "enum": [
                  "input_identity_mismatch",
                  "dependency_unavailable",
                  "database_kind_conflict",
                  "native_start_failed",
                  "native_nonzero_exit",
                  "output_missing",
                  "output_inventory_incomplete",
                  "native_format_unsupported",
                  "native_row_invalid",
                  "native_document_invalid",
                  "record_association_unresolved",
                  "sequence_length_conflict",
                  "selection_incomplete",
                  "original_attempt_conflict",
                  "semantic_validation_unavailable",
                  "sequence_symbol_invalid",
                  "duplicate_native_identity",
                  "input_population_unavailable",
                  "input_sequence_invalid",
                  "database_metadata_conflict",
                  "output_family_incomplete",
                  "preparation_not_successful",
                  "native_diagnostic_unrecognized",
                  "sampled_check_scope",
                  "supplied_binding_conflict",
                  "incompatible_database_format",
                  "native_integrity_failure"
                ]
              },
              {
                "type": "null"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          },
          "status": {
            "enum": [
              "pass",
              "fail",
              "unknown",
              "not_applicable"
            ]
          },
          "subject_refs": {
            "items": {
              "minLength": 1,
              "type": "string"
            },
            "type": "array",
            "uniqueItems": true
          }
        },
        "required": [
          "source_ref",
          "name",
          "status",
          "subject_refs",
          "method",
          "reason",
          "evidence_occurrence_ids"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_checks"
    },
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "evidence_occurrence_ids": {
            "items": {
              "minLength": 1,
              "type": "string"
            },
            "type": "array",
            "uniqueItems": true
          },
          "method": {
            "enum": [
              "identity_digest",
              "family_inventory",
              "native_format_parser",
              "explicit_reference_join",
              "selected_record_match",
              "sequence_length_agreement",
              "native_full_check",
              "native_sample_check",
              "native_execution_outcome"
            ]
          },
          "name": {
            "enum": [
              "custody",
              "syntax",
              "identity",
              "selection",
              "sequence_length",
              "sequence_symbols",
              "database_inventory",
              "database_metadata",
              "native_integrity",
              "native_execution"
            ]
          },
          "reason": {
            "anyOf": [
              {
                "enum": [
                  "input_identity_mismatch",
                  "dependency_unavailable",
                  "database_kind_conflict",
                  "native_start_failed",
                  "native_nonzero_exit",
                  "output_missing",
                  "output_inventory_incomplete",
                  "output_writer_not_closed",
                  "output_completeness_unestablished",
                  "native_outcome_unavailable",
                  "native_format_unsupported",
                  "native_row_invalid",
                  "native_document_invalid",
                  "record_association_unresolved",
                  "sequence_length_conflict",
                  "selection_incomplete",
                  "original_attempt_conflict",
                  "semantic_validation_unavailable",
                  "sequence_symbol_invalid",
                  "duplicate_native_identity",
                  "input_population_unavailable",
                  "input_sequence_invalid",
                  "database_metadata_conflict",
                  "output_family_incomplete",
                  "preparation_not_successful",
                  "native_diagnostic_unrecognized",
                  "sampled_check_scope",
                  "supplied_binding_conflict",
                  "incompatible_database_format",
                  "native_integrity_failure"
                ]
              },
              {
                "type": "null"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          },
          "status": {
            "enum": [
              "pass",
              "fail",
              "unknown",
              "not_applicable"
            ]
          },
          "subject_refs": {
            "items": {
              "minLength": 1,
              "type": "string"
            },
            "type": "array",
            "uniqueItems": true
          }
        },
        "required": [
          "source_ref",
          "name",
          "status",
          "subject_refs",
          "method",
          "reason",
          "evidence_occurrence_ids"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_checks"
    }
  ],
  "execution.blast_utility_database_fields": [
    {
      "items": {
        "anyOf": [
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_title"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_format_version"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "version"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_created_at_native"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_sequence_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "sequences"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_residue_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "nt",
                  "aa",
                  "symbols"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_bytes"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "bytes"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_file_names"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "paths"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_volume_names"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "paths"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          }
        ]
      },
      "type": "array",
      "x-source": "execution.blast_utility_database_fields"
    }
  ],
  "execution.blast_utility_failures": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "code": {
            "enum": [
              "input_identity_mismatch",
              "dependency_unavailable",
              "database_kind_conflict",
              "native_start_failed",
              "native_nonzero_exit",
              "output_missing",
              "output_inventory_incomplete",
              "native_format_unsupported",
              "native_row_invalid",
              "native_document_invalid",
              "record_association_unresolved",
              "sequence_length_conflict",
              "selection_incomplete",
              "original_attempt_conflict",
              "semantic_validation_unavailable",
              "sequence_symbol_invalid",
              "duplicate_native_identity",
              "input_population_unavailable",
              "input_sequence_invalid",
              "database_metadata_conflict",
              "output_family_incomplete",
              "preparation_not_successful",
              "native_diagnostic_unrecognized",
              "sampled_check_scope",
              "supplied_binding_conflict",
              "incompatible_database_format",
              "native_integrity_failure"
            ]
          },
          "line_number": {
            "anyOf": [
              {
                "minimum": 1,
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
          },
          "native_returncode": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
          },
          "occurrence_id": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "record_key": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          },
          "stage": {
            "enum": [
              "request",
              "input",
              "native",
              "capture",
              "parse",
              "association",
              "validation",
              "projection"
            ]
          }
        },
        "required": [
          "source_ref",
          "stage",
          "code",
          "occurrence_id",
          "record_key",
          "line_number",
          "native_returncode"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_failures"
    },
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "code": {
            "enum": [
              "input_identity_mismatch",
              "dependency_unavailable",
              "database_kind_conflict",
              "native_start_failed",
              "native_nonzero_exit",
              "output_missing",
              "output_inventory_incomplete",
              "output_writer_not_closed",
              "output_completeness_unestablished",
              "native_outcome_unavailable",
              "native_format_unsupported",
              "native_row_invalid",
              "native_document_invalid",
              "record_association_unresolved",
              "sequence_length_conflict",
              "selection_incomplete",
              "original_attempt_conflict",
              "semantic_validation_unavailable",
              "sequence_symbol_invalid",
              "duplicate_native_identity",
              "input_population_unavailable",
              "input_sequence_invalid",
              "database_metadata_conflict",
              "output_family_incomplete",
              "preparation_not_successful",
              "native_diagnostic_unrecognized",
              "sampled_check_scope",
              "supplied_binding_conflict",
              "incompatible_database_format",
              "native_integrity_failure"
            ]
          },
          "line_number": {
            "anyOf": [
              {
                "minimum": 1,
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
          },
          "native_returncode": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
          },
          "occurrence_id": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "record_key": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          },
          "stage": {
            "enum": [
              "request",
              "input",
              "native",
              "capture",
              "parse",
              "association",
              "validation",
              "projection"
            ]
          }
        },
        "required": [
          "source_ref",
          "stage",
          "code",
          "occurrence_id",
          "record_key",
          "line_number",
          "native_returncode"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_failures"
    }
  ],
  "execution.blast_utility_integrity": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "database_key": {
            "minLength": 1,
            "type": "string"
          },
          "fields": {
            "additionalProperties": false,
            "properties": {
              "diagnostics": {
                "items": {
                  "additionalProperties": false,
                  "properties": {
                    "category": {
                      "enum": [
                        "check_pass",
                        "check_failure",
                        "execution_failure",
                        "unknown"
                      ]
                    },
                    "line_number": {
                      "minimum": 1,
                      "type": "integer"
                    },
                    "native_oid": {
                      "anyOf": [
                        {
                          "minimum": 0,
                          "type": "integer"
                        },
                        {
                          "type": "null"
                        }
                      ]
                    },
                    "occurrence_id": {
                      "minLength": 1,
                      "type": "string"
                    }
                  },
                  "required": [
                    "occurrence_id",
                    "line_number",
                    "category",
                    "native_oid"
                  ],
                  "type": "object"
                },
                "type": "array"
              },
              "observed_checked_count": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "observed_population_count": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "observed_sampled_oids": {
                "anyOf": [
                  {
                    "items": {
                      "minimum": 0,
                      "type": "integer"
                    },
                    "type": "array",
                    "uniqueItems": true
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "realized_seed": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              }
            },
            "required": [],
            "type": "object"
          },
          "scope": {
            "enum": [
              "all_sequences",
              "selected_sample",
              "unknown"
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "database_key",
          "scope",
          "fields"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_integrity"
    }
  ],
  "execution.blast_utility_missing": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "reason": {
            "enum": [
              "result_unavailable",
              "selection_unavailable",
              "field_unavailable",
              "artifact_unavailable",
              "saved_data_unavailable",
              "prepared_database_unavailable"
            ]
          },
          "request": {
            "anyOf": [
              {
                "additionalProperties": false,
                "properties": {
                  "ordinal": {
                    "minimum": 0,
                    "type": "integer"
                  },
                  "type": {
                    "const": "sequence_selector"
                  }
                },
                "required": [
                  "type",
                  "ordinal"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "field_name": {
                    "enum": [
                      "database_title",
                      "database_format_version",
                      "database_created_at_native",
                      "database_sequence_count",
                      "database_residue_count",
                      "database_bytes",
                      "database_file_names",
                      "database_volume_names"
                    ]
                  },
                  "type": {
                    "const": "database_field"
                  }
                },
                "required": [
                  "type",
                  "field_name"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "type": {
                    "const": "integrity"
                  }
                },
                "required": [
                  "type"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "type": {
                    "const": "preparation"
                  }
                },
                "required": [
                  "type"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "type": {
                    "const": "prepared_database"
                  }
                },
                "required": [
                  "type"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "type": {
                    "const": "checks"
                  }
                },
                "required": [
                  "type"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "slot": {
                    "additionalProperties": false,
                    "properties": {
                      "direction": {
                        "enum": [
                          "input",
                          "output"
                        ]
                      },
                      "ordinal": {
                        "anyOf": [
                          {
                            "minimum": 0,
                            "type": "integer"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "description": "Select one original ordinal, or null explicitly for all occurrences of this direction and role."
                      },
                      "role": {
                        "enum": [
                          "sequence_input",
                          "database_file",
                          "database_metadata",
                          "extracted_sequences",
                          "database_manifest",
                          "taxid_map",
                          "mask_input",
                          "stdout",
                          "stderr",
                          "diagnostics",
                          "preparation_receipt",
                          "input_manifest",
                          "offline_configuration"
                        ]
                      }
                    },
                    "required": [
                      "direction",
                      "role",
                      "ordinal"
                    ],
                    "type": "object"
                  },
                  "type": {
                    "const": "artifact"
                  }
                },
                "required": [
                  "type",
                  "slot"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "kind": {
                    "enum": [
                      "result",
                      "prepared_database"
                    ]
                  },
                  "type": {
                    "const": "saved_data"
                  }
                },
                "required": [
                  "type",
                  "kind"
                ],
                "type": "object"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "request",
          "reason"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_missing"
    }
  ],
  "execution.blast_utility_preparation": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "database_key": {
            "minLength": 1,
            "type": "string"
          },
          "fields": {
            "additionalProperties": false,
            "properties": {
              "argv": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "compatibility": {
                "enum": [
                  "validated",
                  "unverified",
                  "incompatible"
                ]
              },
              "dependencies": {
                "items": {
                  "additionalProperties": false,
                  "properties": {
                    "occurrence_id": {
                      "minLength": 1,
                      "type": "string"
                    },
                    "role": {
                      "enum": [
                        "taxid_map",
                        "mask_input"
                      ]
                    }
                  },
                  "required": [
                    "role",
                    "occurrence_id"
                  ],
                  "type": "object"
                },
                "type": "array"
              },
              "detail": {
                "additionalProperties": false,
                "properties": {
                  "database_format_version": {
                    "enum": [
                      4,
                      5
                    ]
                  },
                  "hash_index": {
                    "type": "boolean"
                  },
                  "input_type": {
                    "const": "fasta"
                  },
                  "mask_occurrence_ids": {
                    "items": {
                      "minLength": 1,
                      "type": "string"
                    },
                    "type": "array",
                    "uniqueItems": true
                  },
                  "parse_seqids": {
                    "type": "boolean"
                  },
                  "taxid": {
                    "anyOf": [
                      {
                        "minimum": 0,
                        "type": "integer"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  },
                  "taxid_map_occurrence_id": {
                    "anyOf": [
                      {
                        "minLength": 1,
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  }
                },
                "required": [
                  "input_type",
                  "database_format_version",
                  "parse_seqids",
                  "hash_index",
                  "taxid",
                  "taxid_map_occurrence_id",
                  "mask_occurrence_ids"
                ],
                "type": "object"
              },
              "identity": {
                "additionalProperties": false,
                "properties": {
                  "namespace": {
                    "minLength": 1,
                    "pattern": "^[^\\x00]+$",
                    "type": "string"
                  },
                  "preparation_type": {
                    "const": "sequence_database"
                  },
                  "release": {
                    "anyOf": [
                      {
                        "minLength": 1,
                        "pattern": "^[^\\x00]+$",
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  },
                  "scope": {
                    "anyOf": [
                      {
                        "minLength": 1,
                        "pattern": "^[^\\x00]+$",
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  },
                  "source": {
                    "additionalProperties": false,
                    "properties": {
                      "pointer": {
                        "type": "string"
                      },
                      "source_ref": {
                        "minLength": 1,
                        "pattern": "^[^\\x00]+$",
                        "type": "string"
                      }
                    },
                    "required": [
                      "source_ref",
                      "pointer"
                    ],
                    "type": "object"
                  },
                  "value": {
                    "minLength": 1,
                    "pattern": "^[^\\x00]+$",
                    "type": "string"
                  },
                  "version": {
                    "anyOf": [
                      {
                        "minLength": 1,
                        "pattern": "^[^\\x00]+$",
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  }
                },
                "required": [
                  "namespace",
                  "value",
                  "version",
                  "release",
                  "scope",
                  "preparation_type",
                  "source"
                ],
                "type": "object"
              },
              "inventory_complete": {
                "type": "boolean"
              },
              "native_paths": {
                "items": {
                  "minLength": 1,
                  "type": "string"
                },
                "minItems": 1,
                "type": "array",
                "uniqueItems": true
              },
              "software": {
                "additionalProperties": false,
                "properties": {
                  "executable_sha256": {
                    "anyOf": [
                      {
                        "pattern": "[0-9a-f]{64}",
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  },
                  "name": {
                    "type": "string"
                  },
                  "version": {
                    "anyOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  }
                },
                "required": [
                  "name",
                  "version",
                  "executable_sha256"
                ],
                "type": "object"
              }
            },
            "required": [],
            "type": "object"
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "database_key",
          "fields"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_preparation"
    }
  ],
  "execution.blast_utility_prepared_database": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "database_key": {
            "minLength": 1,
            "type": "string"
          },
          "failures": {
            "items": {
              "additionalProperties": false,
              "properties": {
                "code": {
                  "enum": [
                    "input_identity_mismatch",
                    "dependency_unavailable",
                    "database_kind_conflict",
                    "native_start_failed",
                    "native_nonzero_exit",
                    "output_missing",
                    "output_inventory_incomplete",
                    "native_format_unsupported",
                    "native_row_invalid",
                    "native_document_invalid",
                    "record_association_unresolved",
                    "sequence_length_conflict",
                    "selection_incomplete",
                    "original_attempt_conflict",
                    "semantic_validation_unavailable",
                    "sequence_symbol_invalid",
                    "duplicate_native_identity",
                    "input_population_unavailable",
                    "input_sequence_invalid",
                    "database_metadata_conflict",
                    "output_family_incomplete",
                    "preparation_not_successful",
                    "native_diagnostic_unrecognized",
                    "sampled_check_scope",
                    "supplied_binding_conflict",
                    "incompatible_database_format",
                    "native_integrity_failure"
                  ]
                },
                "line_number": {
                  "anyOf": [
                    {
                      "minimum": 1,
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "native_returncode": {
                  "anyOf": [
                    {
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "occurrence_id": {
                  "anyOf": [
                    {
                      "minLength": 1,
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "record_key": {
                  "anyOf": [
                    {
                      "minLength": 1,
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "stage": {
                  "enum": [
                    "request",
                    "input",
                    "native",
                    "capture",
                    "parse",
                    "association",
                    "validation",
                    "projection"
                  ]
                }
              },
              "required": [
                "stage",
                "code",
                "occurrence_id",
                "record_key",
                "line_number",
                "native_returncode"
              ],
              "type": "object"
            },
            "type": "array"
          },
          "manifest": {
            "anyOf": [
              {
                "additionalProperties": false,
                "properties": {
                  "access": {
                    "additionalProperties": false,
                    "properties": {
                      "mode": {
                        "const": "prepared_local"
                      },
                      "offline_configuration": {
                        "anyOf": [
                          {
                            "additionalProperties": false,
                            "properties": {
                              "artifact_ref": {
                                "anyOf": [
                                  {
                                    "minLength": 1,
                                    "pattern": "^[^\\x00]+$",
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ]
                              },
                              "path": {
                                "minLength": 1,
                                "type": "string"
                              },
                              "sha256": {
                                "pattern": "^[0-9a-f]{64}$",
                                "type": "string"
                              },
                              "size_bytes": {
                                "minimum": 0,
                                "type": "integer"
                              }
                            },
                            "required": [
                              "path",
                              "sha256",
                              "size_bytes",
                              "artifact_ref"
                            ],
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      }
                    },
                    "required": [
                      "mode",
                      "offline_configuration"
                    ],
                    "type": "object"
                  },
                  "database_key": {
                    "minLength": 1,
                    "pattern": "^[^/\\\\\\x00]+$",
                    "type": "string"
                  },
                  "files": {
                    "items": {
                      "additionalProperties": false,
                      "properties": {
                        "path": {
                          "minLength": 1,
                          "type": "string"
                        },
                        "sha256": {
                          "pattern": "^[0-9a-f]{64}$",
                          "type": "string"
                        },
                        "size_bytes": {
                          "minimum": 0,
                          "type": "integer"
                        }
                      },
                      "required": [
                        "path",
                        "sha256",
                        "size_bytes"
                      ],
                      "type": "object"
                    },
                    "minItems": 1,
                    "type": "array"
                  },
                  "identity": {
                    "additionalProperties": false,
                    "properties": {
                      "namespace": {
                        "minLength": 1,
                        "pattern": "^[^\\x00]+$",
                        "type": "string"
                      },
                      "preparation_type": {
                        "const": "sequence_database"
                      },
                      "release": {
                        "anyOf": [
                          {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "scope": {
                        "anyOf": [
                          {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "source": {
                        "additionalProperties": false,
                        "properties": {
                          "pointer": {
                            "type": "string"
                          },
                          "source_ref": {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          }
                        },
                        "required": [
                          "source_ref",
                          "pointer"
                        ],
                        "type": "object"
                      },
                      "value": {
                        "minLength": 1,
                        "pattern": "^[^\\x00]+$",
                        "type": "string"
                      },
                      "version": {
                        "anyOf": [
                          {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      }
                    },
                    "required": [
                      "namespace",
                      "value",
                      "version",
                      "release",
                      "scope",
                      "preparation_type",
                      "source"
                    ],
                    "type": "object"
                  },
                  "inventory_complete": {
                    "type": "boolean"
                  },
                  "kind": {
                    "enum": [
                      "blast_protein_sequence",
                      "blast_nucleotide_sequence"
                    ]
                  },
                  "metadata_manifests": {
                    "items": {
                      "additionalProperties": false,
                      "properties": {
                        "artifact_ref": {
                          "anyOf": [
                            {
                              "minLength": 1,
                              "pattern": "^[^\\x00]+$",
                              "type": "string"
                            },
                            {
                              "type": "null"
                            }
                          ]
                        },
                        "path": {
                          "minLength": 1,
                          "type": "string"
                        },
                        "sha256": {
                          "pattern": "^[0-9a-f]{64}$",
                          "type": "string"
                        },
                        "size_bytes": {
                          "minimum": 0,
                          "type": "integer"
                        }
                      },
                      "required": [
                        "path",
                        "sha256",
                        "size_bytes",
                        "artifact_ref"
                      ],
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "native_paths": {
                    "items": {
                      "minLength": 1,
                      "type": "string"
                    },
                    "minItems": 1,
                    "type": "array",
                    "uniqueItems": true
                  },
                  "preparation": {
                    "additionalProperties": false,
                    "properties": {
                      "argv": {
                        "anyOf": [
                          {
                            "items": {
                              "minLength": 1,
                              "pattern": "^[^\\x00]+$",
                              "type": "string"
                            },
                            "minItems": 1,
                            "type": "array"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "input_manifest": {
                        "anyOf": [
                          {
                            "additionalProperties": false,
                            "properties": {
                              "artifact_ref": {
                                "anyOf": [
                                  {
                                    "minLength": 1,
                                    "pattern": "^[^\\x00]+$",
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ]
                              },
                              "path": {
                                "minLength": 1,
                                "type": "string"
                              },
                              "sha256": {
                                "pattern": "^[0-9a-f]{64}$",
                                "type": "string"
                              },
                              "size_bytes": {
                                "minimum": 0,
                                "type": "integer"
                              }
                            },
                            "required": [
                              "path",
                              "sha256",
                              "size_bytes",
                              "artifact_ref"
                            ],
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "method": {
                        "enum": [
                          "makeblastdb",
                          "publisher_package",
                          "other_recorded"
                        ]
                      },
                      "preparation_type": {
                        "const": "sequence_database"
                      },
                      "receipt": {
                        "additionalProperties": false,
                        "properties": {
                          "artifact_ref": {
                            "anyOf": [
                              {
                                "minLength": 1,
                                "pattern": "^[^\\x00]+$",
                                "type": "string"
                              },
                              {
                                "type": "null"
                              }
                            ]
                          },
                          "path": {
                            "minLength": 1,
                            "type": "string"
                          },
                          "sha256": {
                            "pattern": "^[0-9a-f]{64}$",
                            "type": "string"
                          },
                          "size_bytes": {
                            "minimum": 0,
                            "type": "integer"
                          }
                        },
                        "required": [
                          "path",
                          "sha256",
                          "size_bytes",
                          "artifact_ref"
                        ],
                        "type": "object"
                      },
                      "software": {
                        "additionalProperties": false,
                        "properties": {
                          "executable_sha256": {
                            "anyOf": [
                              {
                                "pattern": "^[0-9a-f]{64}$",
                                "type": "string"
                              },
                              {
                                "type": "null"
                              }
                            ]
                          },
                          "name": {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          },
                          "version": {
                            "anyOf": [
                              {
                                "minLength": 1,
                                "pattern": "^[^\\x00]+$",
                                "type": "string"
                              },
                              {
                                "type": "null"
                              }
                            ]
                          }
                        },
                        "required": [
                          "name",
                          "version",
                          "executable_sha256"
                        ],
                        "type": "object"
                      },
                      "source": {
                        "additionalProperties": false,
                        "properties": {
                          "pointer": {
                            "type": "string"
                          },
                          "source_ref": {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          }
                        },
                        "required": [
                          "source_ref",
                          "pointer"
                        ],
                        "type": "object"
                      }
                    },
                    "required": [
                      "method",
                      "preparation_type",
                      "software",
                      "argv",
                      "source",
                      "input_manifest",
                      "receipt"
                    ],
                    "type": "object"
                  },
                  "version": {
                    "const": "native_blast_standard_prepared_database_manifest_v1"
                  }
                },
                "required": [
                  "version",
                  "database_key",
                  "kind",
                  "identity",
                  "native_paths",
                  "files",
                  "preparation",
                  "metadata_manifests",
                  "access",
                  "inventory_complete"
                ],
                "type": "object"
              },
              {
                "type": "null"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          },
          "status": {
            "enum": [
              "available",
              "unavailable"
            ]
          }
        },
        "required": [
          "source_ref",
          "database_key",
          "status",
          "manifest",
          "failures"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_prepared_database"
    },
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "database_key": {
            "minLength": 1,
            "type": "string"
          },
          "failures": {
            "items": {
              "additionalProperties": false,
              "properties": {
                "code": {
                  "enum": [
                    "input_identity_mismatch",
                    "dependency_unavailable",
                    "database_kind_conflict",
                    "native_start_failed",
                    "native_nonzero_exit",
                    "output_missing",
                    "output_inventory_incomplete",
                    "output_writer_not_closed",
                    "output_completeness_unestablished",
                    "native_outcome_unavailable",
                    "native_format_unsupported",
                    "native_row_invalid",
                    "native_document_invalid",
                    "record_association_unresolved",
                    "sequence_length_conflict",
                    "selection_incomplete",
                    "original_attempt_conflict",
                    "semantic_validation_unavailable",
                    "sequence_symbol_invalid",
                    "duplicate_native_identity",
                    "input_population_unavailable",
                    "input_sequence_invalid",
                    "database_metadata_conflict",
                    "output_family_incomplete",
                    "preparation_not_successful",
                    "native_diagnostic_unrecognized",
                    "sampled_check_scope",
                    "supplied_binding_conflict",
                    "incompatible_database_format",
                    "native_integrity_failure"
                  ]
                },
                "line_number": {
                  "anyOf": [
                    {
                      "minimum": 1,
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "native_returncode": {
                  "anyOf": [
                    {
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "occurrence_id": {
                  "anyOf": [
                    {
                      "minLength": 1,
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "record_key": {
                  "anyOf": [
                    {
                      "minLength": 1,
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "stage": {
                  "enum": [
                    "request",
                    "input",
                    "native",
                    "capture",
                    "parse",
                    "association",
                    "validation",
                    "projection"
                  ]
                }
              },
              "required": [
                "stage",
                "code",
                "occurrence_id",
                "record_key",
                "line_number",
                "native_returncode"
              ],
              "type": "object"
            },
            "type": "array"
          },
          "manifest": {
            "anyOf": [
              {
                "additionalProperties": false,
                "properties": {
                  "access": {
                    "additionalProperties": false,
                    "properties": {
                      "mode": {
                        "const": "prepared_local"
                      },
                      "offline_configuration": {
                        "anyOf": [
                          {
                            "additionalProperties": false,
                            "properties": {
                              "artifact_ref": {
                                "anyOf": [
                                  {
                                    "minLength": 1,
                                    "pattern": "^[^\\x00]+$",
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ]
                              },
                              "path": {
                                "minLength": 1,
                                "type": "string"
                              },
                              "sha256": {
                                "pattern": "^[0-9a-f]{64}$",
                                "type": "string"
                              },
                              "size_bytes": {
                                "minimum": 0,
                                "type": "integer"
                              }
                            },
                            "required": [
                              "path",
                              "sha256",
                              "size_bytes",
                              "artifact_ref"
                            ],
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      }
                    },
                    "required": [
                      "mode",
                      "offline_configuration"
                    ],
                    "type": "object"
                  },
                  "database_key": {
                    "minLength": 1,
                    "pattern": "^[^/\\\\\\x00]+$",
                    "type": "string"
                  },
                  "files": {
                    "items": {
                      "additionalProperties": false,
                      "properties": {
                        "path": {
                          "minLength": 1,
                          "type": "string"
                        },
                        "sha256": {
                          "pattern": "^[0-9a-f]{64}$",
                          "type": "string"
                        },
                        "size_bytes": {
                          "minimum": 0,
                          "type": "integer"
                        }
                      },
                      "required": [
                        "path",
                        "sha256",
                        "size_bytes"
                      ],
                      "type": "object"
                    },
                    "minItems": 1,
                    "type": "array"
                  },
                  "identity": {
                    "additionalProperties": false,
                    "properties": {
                      "namespace": {
                        "minLength": 1,
                        "pattern": "^[^\\x00]+$",
                        "type": "string"
                      },
                      "preparation_type": {
                        "const": "sequence_database"
                      },
                      "release": {
                        "anyOf": [
                          {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "scope": {
                        "anyOf": [
                          {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "source": {
                        "additionalProperties": false,
                        "properties": {
                          "pointer": {
                            "type": "string"
                          },
                          "source_ref": {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          }
                        },
                        "required": [
                          "source_ref",
                          "pointer"
                        ],
                        "type": "object"
                      },
                      "value": {
                        "minLength": 1,
                        "pattern": "^[^\\x00]+$",
                        "type": "string"
                      },
                      "version": {
                        "anyOf": [
                          {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      }
                    },
                    "required": [
                      "namespace",
                      "value",
                      "version",
                      "release",
                      "scope",
                      "preparation_type",
                      "source"
                    ],
                    "type": "object"
                  },
                  "inventory_complete": {
                    "type": "boolean"
                  },
                  "kind": {
                    "enum": [
                      "blast_protein_sequence",
                      "blast_nucleotide_sequence"
                    ]
                  },
                  "metadata_manifests": {
                    "items": {
                      "additionalProperties": false,
                      "properties": {
                        "artifact_ref": {
                          "anyOf": [
                            {
                              "minLength": 1,
                              "pattern": "^[^\\x00]+$",
                              "type": "string"
                            },
                            {
                              "type": "null"
                            }
                          ]
                        },
                        "path": {
                          "minLength": 1,
                          "type": "string"
                        },
                        "sha256": {
                          "pattern": "^[0-9a-f]{64}$",
                          "type": "string"
                        },
                        "size_bytes": {
                          "minimum": 0,
                          "type": "integer"
                        }
                      },
                      "required": [
                        "path",
                        "sha256",
                        "size_bytes",
                        "artifact_ref"
                      ],
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "native_paths": {
                    "items": {
                      "minLength": 1,
                      "type": "string"
                    },
                    "minItems": 1,
                    "type": "array",
                    "uniqueItems": true
                  },
                  "preparation": {
                    "additionalProperties": false,
                    "properties": {
                      "argv": {
                        "anyOf": [
                          {
                            "items": {
                              "minLength": 1,
                              "pattern": "^[^\\x00]+$",
                              "type": "string"
                            },
                            "minItems": 1,
                            "type": "array"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "input_manifest": {
                        "anyOf": [
                          {
                            "additionalProperties": false,
                            "properties": {
                              "artifact_ref": {
                                "anyOf": [
                                  {
                                    "minLength": 1,
                                    "pattern": "^[^\\x00]+$",
                                    "type": "string"
                                  },
                                  {
                                    "type": "null"
                                  }
                                ]
                              },
                              "path": {
                                "minLength": 1,
                                "type": "string"
                              },
                              "sha256": {
                                "pattern": "^[0-9a-f]{64}$",
                                "type": "string"
                              },
                              "size_bytes": {
                                "minimum": 0,
                                "type": "integer"
                              }
                            },
                            "required": [
                              "path",
                              "sha256",
                              "size_bytes",
                              "artifact_ref"
                            ],
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "method": {
                        "enum": [
                          "makeblastdb",
                          "publisher_package",
                          "other_recorded"
                        ]
                      },
                      "preparation_type": {
                        "const": "sequence_database"
                      },
                      "receipt": {
                        "additionalProperties": false,
                        "properties": {
                          "artifact_ref": {
                            "anyOf": [
                              {
                                "minLength": 1,
                                "pattern": "^[^\\x00]+$",
                                "type": "string"
                              },
                              {
                                "type": "null"
                              }
                            ]
                          },
                          "path": {
                            "minLength": 1,
                            "type": "string"
                          },
                          "sha256": {
                            "pattern": "^[0-9a-f]{64}$",
                            "type": "string"
                          },
                          "size_bytes": {
                            "minimum": 0,
                            "type": "integer"
                          }
                        },
                        "required": [
                          "path",
                          "sha256",
                          "size_bytes",
                          "artifact_ref"
                        ],
                        "type": "object"
                      },
                      "software": {
                        "additionalProperties": false,
                        "properties": {
                          "executable_sha256": {
                            "anyOf": [
                              {
                                "pattern": "^[0-9a-f]{64}$",
                                "type": "string"
                              },
                              {
                                "type": "null"
                              }
                            ]
                          },
                          "name": {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          },
                          "version": {
                            "anyOf": [
                              {
                                "minLength": 1,
                                "pattern": "^[^\\x00]+$",
                                "type": "string"
                              },
                              {
                                "type": "null"
                              }
                            ]
                          }
                        },
                        "required": [
                          "name",
                          "version",
                          "executable_sha256"
                        ],
                        "type": "object"
                      },
                      "source": {
                        "additionalProperties": false,
                        "properties": {
                          "pointer": {
                            "type": "string"
                          },
                          "source_ref": {
                            "minLength": 1,
                            "pattern": "^[^\\x00]+$",
                            "type": "string"
                          }
                        },
                        "required": [
                          "source_ref",
                          "pointer"
                        ],
                        "type": "object"
                      }
                    },
                    "required": [
                      "method",
                      "preparation_type",
                      "software",
                      "argv",
                      "source",
                      "input_manifest",
                      "receipt"
                    ],
                    "type": "object"
                  },
                  "version": {
                    "const": "native_blast_standard_prepared_database_manifest_v1"
                  }
                },
                "required": [
                  "version",
                  "database_key",
                  "kind",
                  "identity",
                  "native_paths",
                  "files",
                  "preparation",
                  "metadata_manifests",
                  "access",
                  "inventory_complete"
                ],
                "type": "object"
              },
              {
                "type": "null"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          },
          "status": {
            "enum": [
              "available",
              "unavailable"
            ]
          }
        },
        "required": [
          "source_ref",
          "database_key",
          "status",
          "manifest",
          "failures"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_prepared_database"
    }
  ],
  "execution.blast_utility_saved_data": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "artifact_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "artifact"
          },
          "kind": {
            "enum": [
              "result",
              "prepared_database"
            ]
          },
          "schema": {
            "enum": [
              "blast_sequence_extraction_v1",
              "blast_database_inspection_v1",
              "blast_database_integrity_v1",
              "blast_database_artifact_set_v1",
              "native_blast_standard_prepared_database_manifest_v1"
            ]
          },
          "sha256": {
            "pattern": "[0-9a-f]{64}",
            "type": "string"
          },
          "size_bytes": {
            "minimum": 0,
            "type": "integer"
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "kind",
          "artifact_ref",
          "sha256",
          "size_bytes",
          "schema"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_saved_data"
    }
  ],
  "execution.blast_utility_sequences": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "association": {
            "enum": [
              "exact",
              "explicit",
              "unresolved"
            ]
          },
          "completeness": {
            "enum": [
              "complete",
              "partial",
              "unknown"
            ]
          },
          "database_key": {
            "minLength": 1,
            "type": "string"
          },
          "effective_range": {
            "anyOf": [
              {
                "additionalProperties": false,
                "properties": {
                  "end_exclusive": {
                    "minimum": 0,
                    "type": "integer"
                  },
                  "start_0based": {
                    "minimum": 0,
                    "type": "integer"
                  },
                  "strand": {
                    "enum": [
                      "plus",
                      "minus"
                    ]
                  }
                },
                "required": [
                  "start_0based",
                  "end_exclusive",
                  "strand"
                ],
                "type": "object"
              },
              {
                "type": "null"
              }
            ]
          },
          "line_number": {
            "minimum": 1,
            "type": "integer"
          },
          "molecule": {
            "enum": [
              "dna",
              "protein"
            ]
          },
          "native_accession": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "native_identifier": {
            "type": "string"
          },
          "native_length_basis": {
            "enum": [
              "full_sequence",
              "returned_sequence",
              "unknown"
            ]
          },
          "native_oid": {
            "anyOf": [
              {
                "minimum": 0,
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
          },
          "native_reported_length": {
            "anyOf": [
              {
                "minimum": 0,
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
          },
          "native_row_ordinal": {
            "minimum": 0,
            "type": "integer"
          },
          "occurrence_id": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "native_blast_utility_occurrence"
          },
          "record_key": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "native_blast_utility_record"
          },
          "requested_range": {
            "anyOf": [
              {
                "additionalProperties": false,
                "properties": {
                  "end_1based": {
                    "minimum": 1,
                    "type": "integer"
                  },
                  "start_1based": {
                    "minimum": 1,
                    "type": "integer"
                  }
                },
                "required": [
                  "start_1based",
                  "end_1based"
                ],
                "type": "object"
              },
              {
                "type": "null"
              }
            ]
          },
          "returned_symbol_count": {
            "anyOf": [
              {
                "minimum": 0,
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
          },
          "selector_ordinals": {
            "items": {
              "minimum": 0,
              "type": "integer"
            },
            "minItems": 1,
            "type": "array",
            "uniqueItems": true
          },
          "sequences": {
            "additionalProperties": false,
            "properties": {
              "normalized_sequence": {
                "type": "string"
              },
              "original_sequence": {
                "type": "string"
              }
            },
            "required": [],
            "type": "object"
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "database_key",
          "record_key",
          "occurrence_id",
          "selector_ordinals",
          "native_row_ordinal",
          "line_number",
          "association",
          "native_oid",
          "native_identifier",
          "native_accession",
          "native_reported_length",
          "native_length_basis",
          "returned_symbol_count",
          "molecule",
          "requested_range",
          "effective_range",
          "completeness",
          "sequences"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_sequences"
    }
  ],
  "execution.blast_utility_status": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "inventory_complete": {
            "type": "boolean"
          },
          "native_state": {
            "enum": [
              "succeeded",
              "failed",
              "incomplete",
              "unknown"
            ]
          },
          "result_completeness": {
            "anyOf": [
              {
                "enum": [
                  "complete_selection",
                  "partial_selection",
                  "complete",
                  "partial",
                  "unknown"
                ]
              },
              {
                "type": "null"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          },
          "state": {
            "enum": [
              "complete",
              "partial",
              "failed",
              "unavailable"
            ]
          },
          "writer_closed": {
            "type": "boolean"
          }
        },
        "required": [
          "source_ref",
          "state",
          "native_state",
          "writer_closed",
          "inventory_complete",
          "result_completeness"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_status"
    }
  ]
}
'''


# Exact retained preparation-era fields extracted from the original closed
# check113b tree by bounded529 check130_vdb_historical672. These independent
# documents are not reconstructed from today's expanding fact schemas.
_RETAINED_654_REGISTRY_JSON = r'''
{
  "execution.blast_utility_artifacts": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "artifact_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "artifact"
          },
          "completeness": {
            "enum": [
              "complete",
              "partial",
              "unknown"
            ]
          },
          "direction": {
            "enum": [
              "input",
              "output"
            ]
          },
          "native_format": {
            "enum": [
              "fasta",
              "blastdbcmd_tabular_v1",
              "blastdb_info_text",
              "blastdb_metadata_json",
              "blastdbcheck_text",
              "blastdb_binary",
              "json",
              "text",
              "maskinfo_xml",
              "maskinfo_asn1_text",
              "unknown",
              "gi_list_binary",
              "seqid_list_binary",
              "blast_alias_text",
              "blast_seqid_list_info_text",
              "blast_index_binary",
              "blast_index_map_text",
              "blast_profile_aux_text",
              "pssm_asn1_text",
              "pssm_asn1_binary"
            ]
          },
          "native_path": {
            "anyOf": [
              {
                "minLength": 1,
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "occurrence_id": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "native_blast_utility_occurrence"
          },
          "ordinal": {
            "minimum": 0,
            "type": "integer"
          },
          "role": {
            "enum": [
              "sequence_input",
              "database_file",
              "database_metadata",
              "extracted_sequences",
              "database_manifest",
              "taxid_map",
              "mask_input",
              "stdout",
              "stderr",
              "diagnostics",
              "preparation_receipt",
              "input_manifest",
              "offline_configuration",
              "identifier_list",
              "database_list",
              "profile_list",
              "profile_input",
              "materialized_list",
              "alias_file",
              "index_file",
              "profile_file",
              "statistics"
            ]
          },
          "sha256": {
            "pattern": "[0-9a-f]{64}",
            "type": "string"
          },
          "size_bytes": {
            "minimum": 0,
            "type": "integer"
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "occurrence_id",
          "direction",
          "role",
          "ordinal",
          "artifact_ref",
          "sha256",
          "size_bytes",
          "native_format",
          "completeness",
          "native_path"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_artifacts"
    }
  ],
  "execution.blast_utility_database_fields": [
    {
      "items": {
        "anyOf": [
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_title"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_format_version"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "version"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_created_at_native"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_sequence_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "sequences"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_residue_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "nt",
                  "aa",
                  "symbols"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_bytes"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "bytes"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_file_names"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "paths"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "database_volume_names"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "paths"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "identifier_list_title"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "identifier_list_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "identifiers"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "identifier_list_converted_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "identifier_occurrences"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "identifier_list_created_at_native"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "identifier_list_database_created_at_native"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "identifier_list_database_length"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "nt",
                  "aa",
                  "symbols"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "database_key": {
                "minLength": 1,
                "type": "string"
              },
              "field_name": {
                "const": "identifier_list_database_volumes"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "unit": {
                "enum": [
                  "paths"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "database_key",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "database_title"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "database_format_version"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "version"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "database_created_at_native"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "database_sequence_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "sequences"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "database_residue_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "nt",
                  "aa",
                  "symbols"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "database_bytes"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "bytes"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "database_file_names"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "paths"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "database_volume_names"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "paths"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "identifier_list_title"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "identifier_list_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "identifiers"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "identifier_list_converted_count"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "identifier_occurrences"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "identifier_list_created_at_native"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "identifier_list_database_created_at_native"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "text"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "identifier_list_database_length"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "nt",
                  "aa",
                  "symbols"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "minimum": 0,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          },
          {
            "additionalProperties": false,
            "properties": {
              "field_name": {
                "const": "identifier_list_database_volumes"
              },
              "json_pointer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "line_number": {
                "anyOf": [
                  {
                    "minimum": 1,
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "missing_reason": {
                "anyOf": [
                  {
                    "enum": [
                      "native_field_absent",
                      "native_field_invalid",
                      "ambiguous_population"
                    ]
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "native_lexeme": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "occurrence_id": {
                "minLength": 1,
                "type": "string"
              },
              "source_ref": {
                "format": "reference",
                "minLength": 1,
                "type": "string",
                "x-reference-namespace": "execution_result"
              },
              "subject": {
                "anyOf": [
                  {
                    "additionalProperties": false,
                    "properties": {
                      "kind": {
                        "const": "identifier_list"
                      },
                      "occurrence_id": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "occurrence_id"
                    ],
                    "type": "object"
                  },
                  {
                    "additionalProperties": false,
                    "properties": {
                      "database_key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "kind": {
                        "const": "database"
                      }
                    },
                    "required": [
                      "kind",
                      "database_key"
                    ],
                    "type": "object"
                  }
                ]
              },
              "unit": {
                "enum": [
                  "paths"
                ]
              },
              "value": {
                "anyOf": [
                  {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "value_basis": {
                "enum": [
                  "native_reported",
                  "native_reported_exact",
                  "native_reported_approximate"
                ]
              }
            },
            "required": [
              "source_ref",
              "subject",
              "field_name",
              "value",
              "unit",
              "value_basis",
              "native_lexeme",
              "occurrence_id",
              "line_number",
              "json_pointer",
              "missing_reason"
            ],
            "type": "object"
          }
        ]
      },
      "type": "array",
      "x-source": "execution.blast_utility_database_fields"
    }
  ],
  "execution.blast_utility_missing": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "reason": {
            "enum": [
              "result_unavailable",
              "selection_unavailable",
              "field_unavailable",
              "artifact_unavailable",
              "saved_data_unavailable",
              "prepared_database_unavailable"
            ]
          },
          "request": {
            "anyOf": [
              {
                "additionalProperties": false,
                "properties": {
                  "ordinal": {
                    "minimum": 0,
                    "type": "integer"
                  },
                  "type": {
                    "const": "sequence_selector"
                  }
                },
                "required": [
                  "type",
                  "ordinal"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "field_name": {
                    "enum": [
                      "database_title",
                      "database_format_version",
                      "database_created_at_native",
                      "database_sequence_count",
                      "database_residue_count",
                      "database_bytes",
                      "database_file_names",
                      "database_volume_names",
                      "identifier_list_title",
                      "identifier_list_count",
                      "identifier_list_converted_count",
                      "identifier_list_created_at_native",
                      "identifier_list_database_created_at_native",
                      "identifier_list_database_length",
                      "identifier_list_database_volumes"
                    ]
                  },
                  "type": {
                    "const": "database_field"
                  }
                },
                "required": [
                  "type",
                  "field_name"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "type": {
                    "const": "integrity"
                  }
                },
                "required": [
                  "type"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "type": {
                    "const": "preparation"
                  }
                },
                "required": [
                  "type"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "type": {
                    "const": "prepared_database"
                  }
                },
                "required": [
                  "type"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "type": {
                    "const": "checks"
                  }
                },
                "required": [
                  "type"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "slot": {
                    "additionalProperties": false,
                    "properties": {
                      "direction": {
                        "enum": [
                          "input",
                          "output"
                        ]
                      },
                      "ordinal": {
                        "anyOf": [
                          {
                            "minimum": 0,
                            "type": "integer"
                          },
                          {
                            "type": "null"
                          }
                        ],
                        "description": "Select one original ordinal, or null explicitly for all occurrences of this direction and role."
                      },
                      "role": {
                        "enum": [
                          "sequence_input",
                          "database_file",
                          "database_metadata",
                          "extracted_sequences",
                          "database_manifest",
                          "taxid_map",
                          "mask_input",
                          "stdout",
                          "stderr",
                          "diagnostics",
                          "preparation_receipt",
                          "input_manifest",
                          "offline_configuration",
                          "identifier_list",
                          "database_list",
                          "profile_list",
                          "profile_input",
                          "materialized_list",
                          "alias_file",
                          "index_file",
                          "profile_file",
                          "statistics"
                        ]
                      }
                    },
                    "required": [
                      "direction",
                      "role",
                      "ordinal"
                    ],
                    "type": "object"
                  },
                  "type": {
                    "const": "artifact"
                  }
                },
                "required": [
                  "type",
                  "slot"
                ],
                "type": "object"
              },
              {
                "additionalProperties": false,
                "properties": {
                  "kind": {
                    "enum": [
                      "result",
                      "prepared_database"
                    ]
                  },
                  "type": {
                    "const": "saved_data"
                  }
                },
                "required": [
                  "type",
                  "kind"
                ],
                "type": "object"
              }
            ]
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "request",
          "reason"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_missing"
    }
  ],
  "execution.blast_utility_saved_data": [
    {
      "items": {
        "additionalProperties": false,
        "properties": {
          "artifact_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "artifact"
          },
          "kind": {
            "enum": [
              "result",
              "prepared_database"
            ]
          },
          "schema": {
            "enum": [
              "blast_sequence_extraction_v1",
              "blast_database_inspection_v1",
              "blast_database_integrity_v1",
              "blast_database_artifact_set_v1",
              "blast_database_inspection_v2",
              "blast_database_artifact_set_v2",
              "native_blast_standard_prepared_database_manifest_v1",
              "native_blast_prepared_database_manifest_v1"
            ]
          },
          "sha256": {
            "pattern": "[0-9a-f]{64}",
            "type": "string"
          },
          "size_bytes": {
            "minimum": 0,
            "type": "integer"
          },
          "source_ref": {
            "format": "reference",
            "minLength": 1,
            "type": "string",
            "x-reference-namespace": "execution_result"
          }
        },
        "required": [
          "source_ref",
          "kind",
          "artifact_ref",
          "sha256",
          "size_bytes",
          "schema"
        ],
        "type": "object"
      },
      "type": "array",
      "x-source": "execution.blast_utility_saved_data"
    }
  ]
}
'''

_RETAINED_654_PROVENANCE_JSON = r'''
{
  "check113b_workflow654": {
    "affected_field_uses": 39,
    "extraction": {
      "path": "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check113b_workflow654/check130_vdb_historical672/original_tree_evidence/SCHEMA_AUDIT_001.json",
      "sha256": "6b5cc6c4695fcba00005d55c7b3f72401a45c85a0c5d83429a804ae1df515375",
      "size_bytes": 1177604
    },
    "first_original_uses": [
      {
        "child_episode_id": "episode_d27cdef27c702905d8b2653ecb9e83456666389f87694f76caa18375e14c58cf",
        "decision_index": 0,
        "field": "database_fields",
        "parent_episode_id": "episode_ba1d1e1494eec35cd2abf8d389882b2cd570a9efa0e8fffa25d0118c66dc8a49",
        "registered": false,
        "run_id": "preparation-workflow654",
        "schema_sha256": "c53cdb73800a6b44efc66d911f26e69247a866773280969e74791491cdcdbc95",
        "source": "execution.blast_utility_database_fields"
      },
      {
        "child_episode_id": "episode_d27cdef27c702905d8b2653ecb9e83456666389f87694f76caa18375e14c58cf",
        "decision_index": 0,
        "field": "missing",
        "parent_episode_id": "episode_ba1d1e1494eec35cd2abf8d389882b2cd570a9efa0e8fffa25d0118c66dc8a49",
        "registered": false,
        "run_id": "preparation-workflow654",
        "schema_sha256": "790db139998ee7b96c79939c144b609d04859f93f8b3fbae50298f4d61e1a3a8",
        "source": "execution.blast_utility_missing"
      },
      {
        "child_episode_id": "episode_d27cdef27c702905d8b2653ecb9e83456666389f87694f76caa18375e14c58cf",
        "decision_index": 0,
        "field": "saved_data",
        "parent_episode_id": "episode_ba1d1e1494eec35cd2abf8d389882b2cd570a9efa0e8fffa25d0118c66dc8a49",
        "registered": false,
        "run_id": "preparation-workflow654",
        "schema_sha256": "773ff91ad5a7bc1948530b5fa3e78d5fc3333a4df75043a1784f990517417fc1",
        "source": "execution.blast_utility_saved_data"
      },
      {
        "child_episode_id": "episode_a8dcbea9fb9b2f3a9888f12d7f4f8a6081bd8a4469fa5fe67ee63d5cc32fc287",
        "decision_index": 1,
        "field": "artifacts",
        "parent_episode_id": "episode_d27cdef27c702905d8b2653ecb9e83456666389f87694f76caa18375e14c58cf",
        "registered": false,
        "run_id": "preparation-workflow654",
        "schema_sha256": "fc1af08156e6cd6c062567fe32508e045e4a0789e7e7dc3536e5545e9f11e9f8",
        "source": "execution.blast_utility_artifacts"
      }
    ],
    "original_deliveries": 10,
    "original_sqlite": {
      "path": "/home/chia/repos/gene_annotation_episode/verification/tool_graders_hmmer_map_verification_2026-10-28_529/check113b_workflow654/temporary/pytest/preparation-workflow6540/state/state.sqlite3",
      "sha256": "f8619eb7cd887fa3bf327d6208b9adcd6bb14fdffae953d3faa0f300d269b767",
      "size_bytes": 80601088
    },
    "schema_documents_sha256": {
      "execution.blast_utility_artifacts": [
        "fc1af08156e6cd6c062567fe32508e045e4a0789e7e7dc3536e5545e9f11e9f8"
      ],
      "execution.blast_utility_database_fields": [
        "c53cdb73800a6b44efc66d911f26e69247a866773280969e74791491cdcdbc95"
      ],
      "execution.blast_utility_missing": [
        "790db139998ee7b96c79939c144b609d04859f93f8b3fbae50298f4d61e1a3a8"
      ],
      "execution.blast_utility_saved_data": [
        "773ff91ad5a7bc1948530b5fa3e78d5fc3333a4df75043a1784f990517417fc1"
      ]
    },
    "schema_location": "contract.measurements.schema.properties",
    "source_table": "runtime_report_attempts"
  }
}
'''


def blast_utility_historical_fact_schemas() -> dict[str, tuple[dict, ...]]:
    """Return only the exact prior registrations, grouped by original x-source."""
    registry = json.loads(_HISTORICAL_REGISTRY_JSON)
    for source, schemas in json.loads(_RETAINED_654_REGISTRY_JSON).items():
        registry.setdefault(source, []).extend(schemas)
    return {source: tuple(schemas) for source, schemas in registry.items()}


def blast_utility_historical_schema_provenance() -> dict:
    """Return detached source and full-registration hashes for audit."""
    return {**json.loads(_SOURCE_PROVENANCE_JSON),
            **json.loads(_RETAINED_654_PROVENANCE_JSON)}


__all__ = ["blast_utility_historical_fact_schemas", "blast_utility_historical_schema_provenance"]
