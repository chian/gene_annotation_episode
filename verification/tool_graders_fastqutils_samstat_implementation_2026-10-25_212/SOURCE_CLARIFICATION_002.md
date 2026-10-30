# Additive unknown-mode no-reads banner clarification

Root direction during212 implementation: the genuine2.5.0 empty.fastq report has a SAMStat2.5.0 header but no native input-format label. Source input_format_name leaves an undetected format blank; stat_report emits the no-reads banner when n_total is zero. A filename is not a native mode declaration.

Preserve one available zero `samstat_reported_item_count`, unit `native_count`, meaning `observed_count`, precision `exact_for_retained_population`, axis none, null population, samstat_summary. The count describes contributing items of unknown sequence/alignment type. Emit `source_row_absent` with required_data `native_execution_evidence`. No population, alignment bins, sequence count, or calculator operand is inferred. The version and source bytes stay retained.

This adds one metric to the sealed59; historical207 and COMMON_CONTRACT_MANIFEST_001 remain unchanged. Both earlier requested-form generations keep their exact frozen grammar.
