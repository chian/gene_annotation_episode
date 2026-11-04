"""Native p3-sra quantities, without an acquisition-confidence calculation."""

SRA_FIELDS = {
    'total_bases': ('sra_reported_total_bases', 'bases', 'nonnegative_integer',
                    'Reported run total_bases; not a recount of downloaded reads.'),
    'total_spots': ('sra_reported_total_spots', 'spots', 'nonnegative_integer',
                    'Reported sequencing spots for this run; spots are not reads.'),
    'size': ('sra_reported_archive_bytes', 'bytes', 'nonnegative_integer',
             'Reported archive size, not decompressed FASTQ size or scratch requirement.'),
    'read_length': ('sra_reported_read_length', 'bases', 'nonnegative_number',
                    'Reported actual_read_length or first Statistics average; basis absent from JSON.'),
    'n_reads': ('sra_reported_read_types_per_spot', 'native_count', 'nonnegative_integer',
                'Number of Statistics read types with count>0, or layout fallback1/2; never total reads.'),
}

SRA_METRICS = {
    metric: dict(metric=metric, formats=['sra_metadata'], section_key='sra_run',
        native_fields=[field], units=[unit], axis_kinds=['none'],
        population_keys=['sra_reported_run'], meaning='observed_native',
        precision='not_reported', value_domain=domain, interpretation=description,
        denominator=None, coordinates='not_applicable', uncertainty='not_reported',
        missing_behavior='Absent stays absent; null is not_measured; malformed/duplicate '
            'values cannot become numbers. Preserve zero and independent valid rows.',
        reviewed_source='BV-BRC/sra_import tree ea9d90719ebb56606c42843f54b658a93c9dcadf '
            'lib/sra_tools.py parse_accession_metadata; 210 SRA_IMPLEMENTATION_CONTRACT_001')
    for field, (metric, unit, domain, description) in SRA_FIELDS.items()
}

SRA_DIAGNOSTICS = (
    'sra_metadata_basis_unproven', 'sra_read_length_basis_unproven',
    'sra_read_types_basis_unproven', 'sra_file_association_unproven',
    'sra_cross_reference_association_unproven',
)
