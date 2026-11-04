"""Two exact historical chromatin field trees, frozen before HIC additions.

These are static production data, not a registry or a runtime verification-file
lookup. Original schema IDs and every reference/type restriction remain intact.
"""
from copy import deepcopy
import json

_PROJECTION = json.loads(r'''
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "BooleanComponent": {
      "type": "object",
      "properties": {
        "value": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ]
        },
        "state": {
          "enum": [
            "derived",
            "missing",
            "failed",
            "truncated",
            "incompatible",
            "undefined"
          ]
        },
        "reason": {
          "anyOf": [
            {
              "enum": [
                "input_unavailable",
                "input_digest_mismatch",
                "unsupported_native_format",
                "unsupported_native_version",
                "malformed_native_header",
                "malformed_native_index",
                "native_chunk_unavailable",
                "native_output_partial",
                "native_value_nonfinite",
                "native_value_negative",
                "numerical_overflow",
                "duplicate_native_pixel",
                "invalid_coordinate",
                "population_boundary_not_bin_aligned",
                "population_unavailable",
                "external_native_dependency_unbound",
                "element_assignment_missing",
                "anchor_outside_element",
                "anchor_bin_unavailable",
                "reference_conflict",
                "incompatible_variable_bins",
                "incompatible_matrix_symmetry",
                "normalization_missing",
                "normalization_weight_invalid",
                "normalization_masked_bin",
                "same_bin_not_evaluated",
                "below_minimum_separation",
                "no_valid_distance_pairs",
                "zero_denominator",
                "incomplete_comparison_population",
                "incomplete_window",
                "no_full_windows",
                "zero_variance",
                "boundary_neighbor_unavailable",
                "native_dependency_unavailable",
                "native_nonzero_exit",
                "resource_limit",
                "original_attempt_mismatch",
                "artifact_digest_mismatch",
                "requested_field_unavailable"
              ]
            },
            {
              "type": "null"
            }
          ]
        },
        "population_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        }
      },
      "required": [
        "value",
        "state",
        "reason",
        "population_key"
      ],
      "additionalProperties": false
    },
    "CalculationParameters": {
      "type": "object",
      "properties": {
        "normalization": {
          "$ref": "#/$defs/NormalizationSpec"
        },
        "contact": {
          "anyOf": [
            {
              "$ref": "#/$defs/ContactParameters"
            },
            {
              "type": "null"
            }
          ]
        },
        "insulation": {
          "anyOf": [
            {
              "$ref": "#/$defs/InsulationParameters"
            },
            {
              "type": "null"
            }
          ]
        }
      },
      "required": [
        "normalization",
        "contact",
        "insulation"
      ],
      "additionalProperties": false
    },
    "ContactParameters": {
      "type": "object",
      "properties": {
        "minimum_separation_bins": {
          "type": "integer",
          "minimum": 1
        },
        "fold_threshold": {
          "type": "number",
          "minimum": 0,
          "maximum": 1.7976931348623157e+308
        },
        "threshold_comparison": {
          "const": "strict_gt"
        },
        "expectation": {
          "const": "same_population_distance_mean"
        },
        "missing_policy": {
          "const": "exclude_declared_masked_bins_require_complete_population"
        }
      },
      "required": [
        "minimum_separation_bins",
        "fold_threshold",
        "threshold_comparison",
        "expectation",
        "missing_policy"
      ],
      "additionalProperties": false
    },
    "Failure": {
      "type": "object",
      "properties": {
        "code": {
          "enum": [
            "input_unavailable",
            "input_digest_mismatch",
            "unsupported_native_format",
            "unsupported_native_version",
            "malformed_native_header",
            "malformed_native_index",
            "native_chunk_unavailable",
            "native_output_partial",
            "native_value_nonfinite",
            "native_value_negative",
            "numerical_overflow",
            "duplicate_native_pixel",
            "invalid_coordinate",
            "population_boundary_not_bin_aligned",
            "population_unavailable",
            "external_native_dependency_unbound",
            "element_assignment_missing",
            "anchor_outside_element",
            "anchor_bin_unavailable",
            "reference_conflict",
            "incompatible_variable_bins",
            "incompatible_matrix_symmetry",
            "normalization_missing",
            "normalization_weight_invalid",
            "normalization_masked_bin",
            "same_bin_not_evaluated",
            "below_minimum_separation",
            "no_valid_distance_pairs",
            "zero_denominator",
            "incomplete_comparison_population",
            "incomplete_window",
            "no_full_windows",
            "zero_variance",
            "boundary_neighbor_unavailable",
            "native_dependency_unavailable",
            "native_nonzero_exit",
            "resource_limit",
            "original_attempt_mismatch",
            "artifact_digest_mismatch",
            "requested_field_unavailable"
          ]
        },
        "stage": {
          "enum": [
            "input",
            "native_parse",
            "metadata",
            "execution",
            "capture",
            "calculation",
            "projection",
            "return_validation"
          ]
        },
        "input_key": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
            },
            {
              "type": "null"
            }
          ]
        },
        "population_key": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
            },
            {
              "type": "null"
            }
          ]
        },
        "element_key": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
            },
            {
              "type": "null"
            }
          ]
        },
        "pair_key": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
            },
            {
              "type": "null"
            }
          ]
        },
        "artifact_ref": {
          "anyOf": [
            {
              "type": "string",
              "minLength": 1
            },
            {
              "type": "null"
            }
          ]
        },
        "locator": {
          "anyOf": [
            {
              "$ref": "#/$defs/Locator"
            },
            {
              "type": "null"
            }
          ]
        },
        "field_path": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^/"
            },
            {
              "type": "null"
            }
          ]
        },
        "partial_artifact_refs": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1
          },
          "minItems": 0,
          "uniqueItems": true
        },
        "requirement": {
          "enum": [
            "supplied_contact_file",
            "matching_file_identity",
            "complete_population",
            "explicit_element_assignment",
            "compatible_reference",
            "fixed_bin_grid",
            "selected_weight_vector",
            "positive_denominator",
            "complete_window",
            "original_native_outcome",
            "requested_selected_field",
            "supported_native_format",
            "valid_native_structure",
            "finite_nonnegative_contact_values",
            "finite_positive_weights",
            "bound_dependencies",
            "caller_resource_fit",
            "matching_original_attempt",
            "finite_numerical_result"
          ]
        }
      },
      "required": [
        "code",
        "stage",
        "input_key",
        "population_key",
        "element_key",
        "pair_key",
        "artifact_ref",
        "locator",
        "field_path",
        "partial_artifact_refs",
        "requirement"
      ],
      "additionalProperties": false
    },
    "InsulationParameters": {
      "type": "object",
      "properties": {
        "window_bins": {
          "type": "integer",
          "minimum": 1
        },
        "z_threshold": {
          "type": "number",
          "minimum": -1.7976931348623157e+308,
          "maximum": 1.7976931348623157e+308
        },
        "threshold_comparison": {
          "const": "strict_lt"
        },
        "zscore_ddof": {
          "const": 0
        },
        "boundary_rule": {
          "const": "strict_two_neighbor_minimum"
        },
        "window_end_rule": {
          "const": "all_full_windows"
        },
        "missing_policy": {
          "const": "complete_window"
        }
      },
      "required": [
        "window_bins",
        "z_threshold",
        "threshold_comparison",
        "zscore_ddof",
        "boundary_rule",
        "window_end_rule",
        "missing_policy"
      ],
      "additionalProperties": false
    },
    "Locator": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "native_row"
            },
            "value": {
              "type": "object",
              "properties": {
                "table_path": {
                  "type": "string",
                  "minLength": 1
                },
                "row_index": {
                  "type": "integer",
                  "minimum": 0
                }
              },
              "required": [
                "table_path",
                "row_index"
              ],
              "additionalProperties": false
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "hdf5_path"
            },
            "value": {
              "type": "string",
              "pattern": "^/"
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "hic_block"
            },
            "value": {
              "type": "object",
              "properties": {
                "chromosome1_index": {
                  "type": "integer",
                  "minimum": 0
                },
                "chromosome2_index": {
                  "type": "integer",
                  "minimum": 0
                },
                "resolution_bp": {
                  "type": "integer",
                  "minimum": 1
                },
                "block_id": {
                  "type": "integer",
                  "minimum": 0
                },
                "record_ordinal": {
                  "anyOf": [
                    {
                      "type": "integer",
                      "minimum": 0
                    },
                    {
                      "type": "null"
                    }
                  ]
                }
              },
              "required": [
                "chromosome1_index",
                "chromosome2_index",
                "resolution_bp",
                "block_id",
                "record_ordinal"
              ],
              "additionalProperties": false
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "bed_line"
            },
            "value": {
              "type": "integer",
              "minimum": 1
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "json_pointer"
            },
            "value": {
              "type": "string",
              "pattern": "^(/|$)"
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        }
      ]
    },
    "Measurement": {
      "type": "object",
      "properties": {
        "value": {
          "anyOf": [
            {
              "type": "number",
              "minimum": -1.7976931348623157e+308,
              "maximum": 1.7976931348623157e+308
            },
            {
              "type": "null"
            }
          ]
        },
        "state": {
          "enum": [
            "observed",
            "derived",
            "normalized",
            "missing",
            "not_measured",
            "failed",
            "truncated",
            "incompatible",
            "undefined"
          ]
        },
        "unit": {
          "$ref": "#/$defs/Unit"
        },
        "reason": {
          "anyOf": [
            {
              "enum": [
                "input_unavailable",
                "input_digest_mismatch",
                "unsupported_native_format",
                "unsupported_native_version",
                "malformed_native_header",
                "malformed_native_index",
                "native_chunk_unavailable",
                "native_output_partial",
                "native_value_nonfinite",
                "native_value_negative",
                "numerical_overflow",
                "duplicate_native_pixel",
                "invalid_coordinate",
                "population_boundary_not_bin_aligned",
                "population_unavailable",
                "external_native_dependency_unbound",
                "element_assignment_missing",
                "anchor_outside_element",
                "anchor_bin_unavailable",
                "reference_conflict",
                "incompatible_variable_bins",
                "incompatible_matrix_symmetry",
                "normalization_missing",
                "normalization_weight_invalid",
                "normalization_masked_bin",
                "same_bin_not_evaluated",
                "below_minimum_separation",
                "no_valid_distance_pairs",
                "zero_denominator",
                "incomplete_comparison_population",
                "incomplete_window",
                "no_full_windows",
                "zero_variance",
                "boundary_neighbor_unavailable",
                "native_dependency_unavailable",
                "native_nonzero_exit",
                "resource_limit",
                "original_attempt_mismatch",
                "artifact_digest_mismatch",
                "requested_field_unavailable"
              ]
            },
            {
              "type": "null"
            }
          ]
        },
        "population_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "numerator": {
          "anyOf": [
            {
              "type": "number",
              "minimum": -1.7976931348623157e+308,
              "maximum": 1.7976931348623157e+308
            },
            {
              "type": "null"
            }
          ]
        },
        "denominator": {
          "anyOf": [
            {
              "type": "number",
              "minimum": -1.7976931348623157e+308,
              "maximum": 1.7976931348623157e+308
            },
            {
              "type": "null"
            }
          ]
        },
        "uncertainty": {
          "$ref": "#/$defs/UncertaintyNotMeasured"
        }
      },
      "required": [
        "value",
        "state",
        "unit",
        "reason",
        "population_key",
        "numerator",
        "denominator",
        "uncertainty"
      ],
      "additionalProperties": false,
      "allOf": [
        {
          "if": {
            "properties": {
              "state": {
                "enum": [
                  "observed",
                  "derived",
                  "normalized"
                ]
              }
            }
          },
          "then": {
            "properties": {
              "value": {
                "type": "number",
                "minimum": -1.7976931348623157e+308,
                "maximum": 1.7976931348623157e+308
              },
              "reason": {
                "type": "null"
              }
            }
          },
          "else": {
            "properties": {
              "value": {
                "type": "null"
              }
            }
          }
        }
      ]
    },
    "NormalizationSpec": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "raw"
            },
            "weight_column": {
              "type": "null"
            },
            "convention": {
              "type": "null"
            }
          },
          "required": [
            "kind",
            "weight_column",
            "convention"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "precomputed_weighted"
            },
            "weight_column": {
              "type": "string",
              "minLength": 1
            },
            "convention": {
              "enum": [
                "multiplicative",
                "divisive"
              ]
            }
          },
          "required": [
            "kind",
            "weight_column",
            "convention"
          ],
          "additionalProperties": false
        }
      ]
    },
    "PageResult": {
      "type": "object",
      "properties": {
        "offset": {
          "type": "integer",
          "minimum": 0
        },
        "returned_count": {
          "type": "integer",
          "minimum": 0
        },
        "total_row_count": {
          "anyOf": [
            {
              "type": "integer",
              "minimum": 0
            },
            {
              "type": "null"
            }
          ]
        },
        "has_more": {
          "type": "boolean"
        }
      },
      "required": [
        "offset",
        "returned_count",
        "total_row_count",
        "has_more"
      ],
      "additionalProperties": false
    },
    "ProjectionContactPairsRow": {
      "type": "object",
      "properties": {
        "pair_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "population_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "enhancer_element_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "promoter_element_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "enhancer_bin_id": {
          "anyOf": [
            {
              "type": "integer",
              "minimum": 0
            },
            {
              "type": "null"
            }
          ]
        },
        "promoter_bin_id": {
          "anyOf": [
            {
              "type": "integer",
              "minimum": 0
            },
            {
              "type": "null"
            }
          ]
        },
        "fields": {
          "type": "object",
          "properties": {
            "raw_contact": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "normalized_contact": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "normalized_contact"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "anchor_distance_bp": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "bp"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "bin_separation": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "bins"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "expected_contact": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact",
                            "normalized_contact"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "fold_enrichment": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "dimensionless"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "occurrence_multiplicity": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "above_fold_threshold": {
              "$ref": "#/$defs/BooleanComponent"
            }
          },
          "required": [],
          "additionalProperties": false,
          "minProperties": 1
        },
        "qualifications": {
          "$ref": "#/$defs/RowQualifications"
        }
      },
      "required": [
        "pair_key",
        "population_key",
        "enhancer_element_key",
        "promoter_element_key",
        "enhancer_bin_id",
        "promoter_bin_id",
        "fields",
        "qualifications"
      ],
      "additionalProperties": false
    },
    "ProjectionDistanceExpectationsRow": {
      "type": "object",
      "properties": {
        "population_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "separation_bins": {
          "type": "integer",
          "minimum": 1
        },
        "fields": {
          "type": "object",
          "properties": {
            "nominal_distance_pair_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "masked_distance_pair_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "valid_distance_pair_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "raw_distance_sum": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "raw_distance_sum_squares": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact_squared"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "distance_sum": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact",
                            "normalized_contact"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "distance_sum_squares": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact_squared",
                            "normalized_contact_squared"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "expected_contact": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact",
                            "normalized_contact"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "distance_population_variance": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact_squared",
                            "normalized_contact_squared"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            }
          },
          "required": [],
          "additionalProperties": false,
          "minProperties": 1
        },
        "qualifications": {
          "$ref": "#/$defs/RowQualifications"
        }
      },
      "required": [
        "population_key",
        "separation_bins",
        "fields",
        "qualifications"
      ],
      "additionalProperties": false
    },
    "ProjectionDomainsRow": {
      "type": "object",
      "properties": {
        "domain_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "population_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "left_boundary_bin_id": {
          "type": "integer",
          "minimum": 0
        },
        "right_boundary_bin_id": {
          "type": "integer",
          "minimum": 0
        },
        "fields": {
          "type": "object",
          "properties": {
            "domain_start_bp": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "bp"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "domain_end_bp": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "bp"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "domain_length_bp": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "bp"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "domain_size_kb": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "kb"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            }
          },
          "required": [],
          "additionalProperties": false,
          "minProperties": 1
        },
        "qualifications": {
          "$ref": "#/$defs/RowQualifications"
        }
      },
      "required": [
        "domain_key",
        "population_key",
        "left_boundary_bin_id",
        "right_boundary_bin_id",
        "fields",
        "qualifications"
      ],
      "additionalProperties": false
    },
    "ProjectionInsulationWindowsRow": {
      "type": "object",
      "properties": {
        "population_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "boundary_bin_id": {
          "type": "integer",
          "minimum": 0
        },
        "boundary_ordinal": {
          "type": "integer",
          "minimum": 0
        },
        "fields": {
          "type": "object",
          "properties": {
            "boundary_position_bp": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "bp"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "nominal_window_cell_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "valid_window_cell_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "known_cross_contact_sum": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact",
                            "normalized_contact"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "cross_contact_sum": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact",
                            "normalized_contact"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "cross_contact_mean": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "source_contact_per_pair",
                            "normalized_contact_per_pair"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "insulation_z": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "dimensionless"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "boundary_strength": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "dimensionless"
                          ]
                        }
                      }
                    }
                  }
                }
              ]
            },
            "is_boundary": {
              "$ref": "#/$defs/BooleanComponent"
            }
          },
          "required": [],
          "additionalProperties": false,
          "minProperties": 1
        },
        "qualifications": {
          "$ref": "#/$defs/RowQualifications"
        }
      },
      "required": [
        "population_key",
        "boundary_bin_id",
        "boundary_ordinal",
        "fields",
        "qualifications"
      ],
      "additionalProperties": false
    },
    "ProjectionPopulationMetricsRow": {
      "type": "object",
      "properties": {
        "population_key": {
          "type": "string",
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
        },
        "fields": {
          "type": "object",
          "properties": {
            "bin_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "directed_cell_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "unique_unordered_cell_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "stored_row_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "explicit_zero_row_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "implicit_zero_directed_cell_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "native_nonfinite_directed_cell_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "unavailable_directed_cell_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "requested_pair_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "eligible_pair_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "fold_defined_pair_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "above_threshold_pair_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "distinct_bin_pair_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "nominal_window_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "complete_window_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "omitted_window_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "selected_boundary_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            },
            "domain_count": {
              "allOf": [
                {
                  "$ref": "#/$defs/Measurement"
                },
                {
                  "properties": {
                    "unit": {
                      "properties": {
                        "kind": {
                          "enum": [
                            "count",
                            "contact_pairs"
                          ]
                        }
                      }
                    },
                    "value": {
                      "anyOf": [
                        {
                          "type": "integer",
                          "minimum": 0
                        },
                        {
                          "type": "null"
                        }
                      ]
                    }
                  }
                }
              ]
            }
          },
          "required": [],
          "additionalProperties": false,
          "minProperties": 1
        },
        "qualifications": {
          "$ref": "#/$defs/RowQualifications"
        }
      },
      "required": [
        "population_key",
        "fields",
        "qualifications"
      ],
      "additionalProperties": false
    },
    "RequestedProjection": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "version": {
              "const": "chromatin_interaction_projection_v1"
            },
            "source_sheet_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "parameters": {
              "$ref": "#/$defs/CalculationParameters"
            },
            "kind": {
              "const": "contact_pairs"
            },
            "population_keys": {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "requested_fields": {
              "type": "array",
              "items": {
                "enum": [
                  "raw_contact",
                  "normalized_contact",
                  "anchor_distance_bp",
                  "bin_separation",
                  "expected_contact",
                  "fold_enrichment",
                  "occurrence_multiplicity",
                  "above_fold_threshold"
                ]
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "rows": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/ProjectionContactPairsRow"
              },
              "minItems": 0
            },
            "page": {
              "anyOf": [
                {
                  "$ref": "#/$defs/PageResult"
                },
                {
                  "type": "null"
                }
              ]
            },
            "qualifications": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/RowQualifications"
              },
              "minItems": 0
            },
            "failures": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/Failure"
              },
              "minItems": 0
            }
          },
          "required": [
            "version",
            "source_sheet_sha256",
            "parameters",
            "kind",
            "population_keys",
            "requested_fields",
            "rows",
            "page",
            "qualifications",
            "failures"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "version": {
              "const": "chromatin_interaction_projection_v1"
            },
            "source_sheet_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "parameters": {
              "$ref": "#/$defs/CalculationParameters"
            },
            "kind": {
              "const": "distance_expectations"
            },
            "population_keys": {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "requested_fields": {
              "type": "array",
              "items": {
                "enum": [
                  "nominal_distance_pair_count",
                  "masked_distance_pair_count",
                  "valid_distance_pair_count",
                  "raw_distance_sum",
                  "raw_distance_sum_squares",
                  "distance_sum",
                  "distance_sum_squares",
                  "expected_contact",
                  "distance_population_variance"
                ]
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "rows": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/ProjectionDistanceExpectationsRow"
              },
              "minItems": 0
            },
            "page": {
              "anyOf": [
                {
                  "$ref": "#/$defs/PageResult"
                },
                {
                  "type": "null"
                }
              ]
            },
            "qualifications": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/RowQualifications"
              },
              "minItems": 0
            },
            "failures": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/Failure"
              },
              "minItems": 0
            }
          },
          "required": [
            "version",
            "source_sheet_sha256",
            "parameters",
            "kind",
            "population_keys",
            "requested_fields",
            "rows",
            "page",
            "qualifications",
            "failures"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "version": {
              "const": "chromatin_interaction_projection_v1"
            },
            "source_sheet_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "parameters": {
              "$ref": "#/$defs/CalculationParameters"
            },
            "kind": {
              "const": "insulation_windows"
            },
            "population_keys": {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "requested_fields": {
              "type": "array",
              "items": {
                "enum": [
                  "boundary_position_bp",
                  "nominal_window_cell_count",
                  "valid_window_cell_count",
                  "known_cross_contact_sum",
                  "cross_contact_sum",
                  "cross_contact_mean",
                  "insulation_z",
                  "boundary_strength",
                  "is_boundary"
                ]
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "rows": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/ProjectionInsulationWindowsRow"
              },
              "minItems": 0
            },
            "page": {
              "anyOf": [
                {
                  "$ref": "#/$defs/PageResult"
                },
                {
                  "type": "null"
                }
              ]
            },
            "qualifications": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/RowQualifications"
              },
              "minItems": 0
            },
            "failures": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/Failure"
              },
              "minItems": 0
            }
          },
          "required": [
            "version",
            "source_sheet_sha256",
            "parameters",
            "kind",
            "population_keys",
            "requested_fields",
            "rows",
            "page",
            "qualifications",
            "failures"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "version": {
              "const": "chromatin_interaction_projection_v1"
            },
            "source_sheet_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "parameters": {
              "$ref": "#/$defs/CalculationParameters"
            },
            "kind": {
              "const": "domains"
            },
            "population_keys": {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "requested_fields": {
              "type": "array",
              "items": {
                "enum": [
                  "domain_start_bp",
                  "domain_end_bp",
                  "domain_length_bp",
                  "domain_size_kb"
                ]
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "rows": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/ProjectionDomainsRow"
              },
              "minItems": 0
            },
            "page": {
              "anyOf": [
                {
                  "$ref": "#/$defs/PageResult"
                },
                {
                  "type": "null"
                }
              ]
            },
            "qualifications": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/RowQualifications"
              },
              "minItems": 0
            },
            "failures": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/Failure"
              },
              "minItems": 0
            }
          },
          "required": [
            "version",
            "source_sheet_sha256",
            "parameters",
            "kind",
            "population_keys",
            "requested_fields",
            "rows",
            "page",
            "qualifications",
            "failures"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "version": {
              "const": "chromatin_interaction_projection_v1"
            },
            "source_sheet_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "parameters": {
              "$ref": "#/$defs/CalculationParameters"
            },
            "kind": {
              "const": "population_metrics"
            },
            "population_keys": {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "requested_fields": {
              "type": "array",
              "items": {
                "enum": [
                  "bin_count",
                  "directed_cell_count",
                  "unique_unordered_cell_count",
                  "stored_row_count",
                  "explicit_zero_row_count",
                  "implicit_zero_directed_cell_count",
                  "native_nonfinite_directed_cell_count",
                  "unavailable_directed_cell_count",
                  "requested_pair_count",
                  "eligible_pair_count",
                  "fold_defined_pair_count",
                  "above_threshold_pair_count",
                  "distinct_bin_pair_count",
                  "nominal_window_count",
                  "complete_window_count",
                  "omitted_window_count",
                  "selected_boundary_count",
                  "domain_count"
                ]
              },
              "minItems": 1,
              "uniqueItems": true
            },
            "rows": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/ProjectionPopulationMetricsRow"
              },
              "minItems": 0
            },
            "page": {
              "anyOf": [
                {
                  "$ref": "#/$defs/PageResult"
                },
                {
                  "type": "null"
                }
              ]
            },
            "qualifications": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/RowQualifications"
              },
              "minItems": 0
            },
            "failures": {
              "type": "array",
              "items": {
                "$ref": "#/$defs/Failure"
              },
              "minItems": 0
            }
          },
          "required": [
            "version",
            "source_sheet_sha256",
            "parameters",
            "kind",
            "population_keys",
            "requested_fields",
            "rows",
            "page",
            "qualifications",
            "failures"
          ],
          "additionalProperties": false
        }
      ]
    },
    "RowQualifications": {
      "type": "object",
      "properties": {
        "data_extent": {
          "enum": [
            "complete",
            "partial",
            "unavailable",
            "incompatible"
          ]
        },
        "reference_relation": {
          "enum": [
            "consistent_assertions",
            "conflicting_assertions",
            "unknown"
          ]
        },
        "normalization_kind": {
          "enum": [
            "raw",
            "precomputed_weighted"
          ]
        },
        "normalization_state": {
          "enum": [
            "available",
            "partial",
            "missing",
            "not_requested"
          ]
        },
        "eligibility": {
          "enum": [
            "eligible",
            "below_minimum_separation",
            "reference_unresolved",
            "cell_unavailable",
            "masked_bin",
            "invalid_weight",
            "incomplete_population",
            "incompatible",
            "ineligible_edge",
            "undefined_statistic",
            "not_applicable"
          ]
        },
        "interpretation": {
          "enum": [
            "complete_population",
            "known_subset",
            "heuristic_prediction"
          ]
        },
        "reasons": {
          "type": "array",
          "items": {
            "enum": [
              "input_unavailable",
              "input_digest_mismatch",
              "unsupported_native_format",
              "unsupported_native_version",
              "malformed_native_header",
              "malformed_native_index",
              "native_chunk_unavailable",
              "native_output_partial",
              "native_value_nonfinite",
              "native_value_negative",
              "numerical_overflow",
              "duplicate_native_pixel",
              "invalid_coordinate",
              "population_boundary_not_bin_aligned",
              "population_unavailable",
              "external_native_dependency_unbound",
              "element_assignment_missing",
              "anchor_outside_element",
              "anchor_bin_unavailable",
              "reference_conflict",
              "incompatible_variable_bins",
              "incompatible_matrix_symmetry",
              "normalization_missing",
              "normalization_weight_invalid",
              "normalization_masked_bin",
              "same_bin_not_evaluated",
              "below_minimum_separation",
              "no_valid_distance_pairs",
              "zero_denominator",
              "incomplete_comparison_population",
              "incomplete_window",
              "no_full_windows",
              "zero_variance",
              "boundary_neighbor_unavailable",
              "native_dependency_unavailable",
              "native_nonzero_exit",
              "resource_limit",
              "original_attempt_mismatch",
              "artifact_digest_mismatch",
              "requested_field_unavailable"
            ]
          },
          "minItems": 0,
          "uniqueItems": true
        }
      },
      "required": [
        "data_extent",
        "reference_relation",
        "normalization_kind",
        "normalization_state",
        "eligibility",
        "interpretation",
        "reasons"
      ],
      "additionalProperties": false
    },
    "UncertaintyNotMeasured": {
      "type": "object",
      "properties": {
        "kind": {
          "const": "not_measured"
        },
        "value": {
          "type": "null"
        },
        "unit": {
          "type": "null"
        }
      },
      "required": [
        "kind",
        "value",
        "unit"
      ],
      "additionalProperties": false
    },
    "Unit": {
      "type": "object",
      "properties": {
        "kind": {
          "enum": [
            "bp",
            "kb",
            "bins",
            "count",
            "contact_pairs",
            "source_contact",
            "source_contact_squared",
            "normalized_contact",
            "normalized_contact_squared",
            "source_contact_per_pair",
            "normalized_contact_per_pair",
            "dimensionless"
          ]
        },
        "source_unit": {
          "anyOf": [
            {
              "type": "string",
              "minLength": 1
            },
            {
              "type": "null"
            }
          ]
        }
      },
      "required": [
        "kind",
        "source_unit"
      ],
      "additionalProperties": false,
      "allOf": [
        {
          "if": {
            "properties": {
              "kind": {
                "enum": [
                  "source_contact",
                  "source_contact_squared",
                  "normalized_contact",
                  "normalized_contact_squared",
                  "source_contact_per_pair",
                  "normalized_contact_per_pair"
                ]
              }
            }
          },
          "then": {
            "properties": {
              "source_unit": {
                "type": "string",
                "minLength": 1
              }
            }
          },
          "else": {
            "properties": {
              "source_unit": {
                "type": "null"
              }
            }
          }
        }
      ]
    }
  },
  "type": "array",
  "items": {
    "$ref": "#/$defs/RequestedProjection"
  },
  "x-source": "chromatin_interaction_projection",
  "$id": "urn:gene-annotation:chromatin:return:1ba0f49fee68561bf3ce14354a05629212dcb55256d129862a96533396805447"
}
''')
_FAILURES = json.loads(r'''
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Failure": {
      "type": "object",
      "properties": {
        "code": {
          "enum": [
            "input_unavailable",
            "input_digest_mismatch",
            "unsupported_native_format",
            "unsupported_native_version",
            "malformed_native_header",
            "malformed_native_index",
            "native_chunk_unavailable",
            "native_output_partial",
            "native_value_nonfinite",
            "native_value_negative",
            "numerical_overflow",
            "duplicate_native_pixel",
            "invalid_coordinate",
            "population_boundary_not_bin_aligned",
            "population_unavailable",
            "external_native_dependency_unbound",
            "element_assignment_missing",
            "anchor_outside_element",
            "anchor_bin_unavailable",
            "reference_conflict",
            "incompatible_variable_bins",
            "incompatible_matrix_symmetry",
            "normalization_missing",
            "normalization_weight_invalid",
            "normalization_masked_bin",
            "same_bin_not_evaluated",
            "below_minimum_separation",
            "no_valid_distance_pairs",
            "zero_denominator",
            "incomplete_comparison_population",
            "incomplete_window",
            "no_full_windows",
            "zero_variance",
            "boundary_neighbor_unavailable",
            "native_dependency_unavailable",
            "native_nonzero_exit",
            "resource_limit",
            "original_attempt_mismatch",
            "artifact_digest_mismatch",
            "requested_field_unavailable"
          ]
        },
        "stage": {
          "enum": [
            "input",
            "native_parse",
            "metadata",
            "execution",
            "capture",
            "calculation",
            "projection",
            "return_validation"
          ]
        },
        "input_key": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
            },
            {
              "type": "null"
            }
          ]
        },
        "population_key": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
            },
            {
              "type": "null"
            }
          ]
        },
        "element_key": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
            },
            {
              "type": "null"
            }
          ]
        },
        "pair_key": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$"
            },
            {
              "type": "null"
            }
          ]
        },
        "artifact_ref": {
          "anyOf": [
            {
              "type": "string",
              "minLength": 1
            },
            {
              "type": "null"
            }
          ]
        },
        "locator": {
          "anyOf": [
            {
              "$ref": "#/$defs/Locator"
            },
            {
              "type": "null"
            }
          ]
        },
        "field_path": {
          "anyOf": [
            {
              "type": "string",
              "pattern": "^/"
            },
            {
              "type": "null"
            }
          ]
        },
        "partial_artifact_refs": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1
          },
          "minItems": 0,
          "uniqueItems": true
        },
        "requirement": {
          "enum": [
            "supplied_contact_file",
            "matching_file_identity",
            "complete_population",
            "explicit_element_assignment",
            "compatible_reference",
            "fixed_bin_grid",
            "selected_weight_vector",
            "positive_denominator",
            "complete_window",
            "original_native_outcome",
            "requested_selected_field",
            "supported_native_format",
            "valid_native_structure",
            "finite_nonnegative_contact_values",
            "finite_positive_weights",
            "bound_dependencies",
            "caller_resource_fit",
            "matching_original_attempt",
            "finite_numerical_result"
          ]
        }
      },
      "required": [
        "code",
        "stage",
        "input_key",
        "population_key",
        "element_key",
        "pair_key",
        "artifact_ref",
        "locator",
        "field_path",
        "partial_artifact_refs",
        "requirement"
      ],
      "additionalProperties": false
    },
    "Locator": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "native_row"
            },
            "value": {
              "type": "object",
              "properties": {
                "table_path": {
                  "type": "string",
                  "minLength": 1
                },
                "row_index": {
                  "type": "integer",
                  "minimum": 0
                }
              },
              "required": [
                "table_path",
                "row_index"
              ],
              "additionalProperties": false
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "hdf5_path"
            },
            "value": {
              "type": "string",
              "pattern": "^/"
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "hic_block"
            },
            "value": {
              "type": "object",
              "properties": {
                "chromosome1_index": {
                  "type": "integer",
                  "minimum": 0
                },
                "chromosome2_index": {
                  "type": "integer",
                  "minimum": 0
                },
                "resolution_bp": {
                  "type": "integer",
                  "minimum": 1
                },
                "block_id": {
                  "type": "integer",
                  "minimum": 0
                },
                "record_ordinal": {
                  "anyOf": [
                    {
                      "type": "integer",
                      "minimum": 0
                    },
                    {
                      "type": "null"
                    }
                  ]
                }
              },
              "required": [
                "chromosome1_index",
                "chromosome2_index",
                "resolution_bp",
                "block_id",
                "record_ordinal"
              ],
              "additionalProperties": false
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "bed_line"
            },
            "value": {
              "type": "integer",
              "minimum": 1
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        },
        {
          "type": "object",
          "properties": {
            "kind": {
              "const": "json_pointer"
            },
            "value": {
              "type": "string",
              "pattern": "^(/|$)"
            }
          },
          "required": [
            "kind",
            "value"
          ],
          "additionalProperties": false
        }
      ]
    }
  },
  "type": "array",
  "items": {
    "$ref": "#/$defs/Failure"
  },
  "x-source": "chromatin_interaction_failures",
  "$id": "urn:gene-annotation:chromatin:return:ae45a8a267c4d93d704f92b33e8bf5c903a1e3e70e7042c15b5dafc37318b4c8"
}
''')


def legacy_chromatin_fact_schema(source):
    if source == 'chromatin_interaction_projection':
        return deepcopy(_PROJECTION)
    if source == 'chromatin_interaction_failures':
        return deepcopy(_FAILURES)
    raise ValueError('chromatin_return_unknown_legacy_source')
