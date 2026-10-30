# Retained GenomeComparison host example

This example uses synthetic native JSON and controlled transport through the real configured AppService host. The selected result assignment is frozen before acquisition; its document selection names requirement `native` and contains no future source or artifact identity. Actual acquisition, publication, native parsing, supplied-input readers, joins, sheet construction, calculation, and typed communication create the retained records in `numerical_example_final_002/`.

| Quantity | Input or calculation | Saved value |
| --- | --- | --- |
| First-HSP identity fraction, row 0 | Native `comp_genome_2_percent_identity` | 0.875 |
| First-HSP identity fraction, row 1 | Native `comp_genome_2_percent_identity` | 0.000 |
| Mean first-HSP identity fraction | `(0.875 + 0.000) / 2` | 0.4375 |
| Subject endpoint-difference fraction, row 0 | Native `comp_genome_2_seq_coverage` | 0.750 |
| Subject endpoint-difference fraction, row 1 | Native `comp_genome_2_seq_coverage` | 0.500 |
| Mean subject endpoint-difference fraction | `(0.750 + 0.500) / 2` | 0.625 |
| Native association records | Two supplied native rows | 2 |
| Selected association count | Identity at least 0.6 and endpoint difference at least 0.7 | 1 |
| Recalculated selected association count | Identity at least 0.9 and endpoint difference at least 0.7 | 0 |
| Executed reference input count | No execution witness supplied | Missing input |
| Executed comparison input count | No execution witness supplied | Missing input |

The two means describe the retained two-row projection. Both summary populations have value count two, with native rounding quantum 0.001. Measured zero remains a value. These are fractions from the legacy projection; the endpoint difference is not full alignment coverage or an annotation-confidence probability. A complete alignment, all-HSP union, exact executed input denominator, or missing source correspondence is not inferred from these values.

The real B1 path reads the retained submission wrapper at `/prepared/native_operands/call/rpc_request/params/1`, two supplied FASTA inventories, and feature, genome, and sequence metadata. Supplied snapshots keep their stated completeness and population qualifications. B2 has no invented native links; its missing joins remain explicit. B3 and B4 retain that missingness while producing the available native measurements and selection counts.

`TYPED_FORM.json` contains 13 requested rows across all eight fact families: five measurements, one ratio, two populations, and one each of associations, selections, requirements, qualifications, and request status. Top-level rows name their actual publication source. Nested source fields also carry native-document and supplied reference-inventory custody. The host test delivers the same requested facts through results → scientific child → its commissioned scientific parent. The outer annotation root requested no form and receives an empty fact map.

`RECALCULATE_EXAMPLE_001.py` separately reads `SHEET.json` and calls the unchanged deterministic calculator with the new threshold. It disables acquisition and native constructors, verifies the original sheet bytes and numerical sheet digest are unchanged, and writes `RECALCULATED_COMPONENTS.json`. `RECALCULATION_001.log` records the actual interpreter, candidate calculator module, parameters, digests, zero acquisition count, and selection change.

Artifacts remain separate:

- `ASSIGNMENT.json`: frozen results selector and provider parameters.
- `SUBMISSION.json` and `submitted_request_wrapper.json`: host submission record and retained native-source wrapper.
- `NATIVE_ACQUISITION.json` and `native.json`: actual acquired artifact record and complete supplied native bytes.
- `SUPPLIED_DATA.json`: supplied metadata selection and constructor inputs.
- `PUBLICATION.json`: actual saved AppService publication.
- `SHEET.json`, `COMPONENTS.json`, and `RECALCULATED_COMPONENTS.json`: populated provider sheet and two explicit numerical calculations.
- `TYPED_FORM.json` and `RECEIVED.json`: requested typed form and received facts.
- `COMMANDS.json`: actual selected native transport calls recorded by the controlled client.

This is host integration with controlled data and transport. The TSV variant is exercised independently by the complete host test group. It does not establish a complete model-driven Workflow, configured-provider model presentation, live BV-BRC execution, or authentication.
