"""Concrete SAMstat native/component descriptions; no executable scoring language.

Sealed207 revision002 plus root-authorized212 unknown-input-kind banner.
Descriptions preserve version-specific populations and native precision.
"""

SAMSTAT_METRICS = {'samstat_alignment_bin_count': {'metric': 'samstat_alignment_bin_count',
                                 'formats': ['samstat_html_2_2_3', 'samstat_html_2_5_0'],
                                 'section_key': 'samstat_mapping',
                                 'native_fields': ['2.2.3 mappingtableval[1 or3][bin0..3]',
                                                   '2.5.0 mapq four rows: Reads / Read1 / Read2 columns'],
                                 'units': ['alignment_records'],
                                 'axis_kinds': ['none', 'mapq', 'native_label'],
                                 'population_keys': ['samstat_report_records',
                                                     'samstat_mapq_ge30',
                                                     'samstat_mapq_10_29',
                                                     'samstat_mapq_0_9',
                                                     'samstat_unmapped',
                                                     'samstat_report_sequences'],
                                 'meaning': 'observed_count',
                                 'precision': 'exact_for_retained_population',
                                 'value_domain': 'nonnegative_integer',
                                 'interpretation': 'Contributing alignment-record count for one native MAPQ bin '
                                                   'and mate/report stratum.2.2.3 excludes secondary but includes '
                                                   'supplementary;2.5.0 excludes both. Native high bin includes '
                                                   'MAPQ255; no read-name deduplication, molecules or pairs.',
                                 'denominator': None,
                                 'coordinates': 'Bin order ge30,10_29,0_9,unmapped,Total. ge30 includes MAPQ 255. '
                                                'MAPQ is not reference coordinate. '
                                                '[30,255],[10,29],[0,9],unmapped flag override. MAPQ255 included '
                                                'in first bin, not known-confidence evidence.',
                                 'uncertainty': 'not reported',
                                 'missing_behavior': 'Missing column is absent, not a zero-filled mate. '
                                                     'Independent complete columns survive truncated HTML. Table '
                                                     'absent for FASTX or no-read report; do not infer alignment '
                                                     'outcomes from sequence-mode plot names.',
                                 'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                 'source_field_ids': ['legacy_mapping_counts', 'modern_mapping_counts'],
                                 'native_precision_description': 'exact integer token exact comma-separated '
                                                                 'integer tokens',
                                 'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                     'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                     'samstat_2_2_3/src/report/stat_report.c',
                                                     'samstat/src/collect/collect.c',
                                                     'samstat/src/htsinterface/htsglue.c',
                                                     'samstat/src/report/stat_report.c'],
                                 'qualifications': ['Native labels MAPQ gt 30 and MAPQ lt 30 are misleading: '
                                                    'exact integer boundaries come from pinned get_mapqual_bins.',
                                                    'The report has no query-name identity or reference '
                                                    'dictionary; counts are not deduplicated reads or pairs.']},
 'samstat_alignment_total_count': {'metric': 'samstat_alignment_total_count',
                                   'formats': ['samstat_html_2_2_3',
                                               'samstat_html_2_5_0',
                                               'samstat_bvbrc_error_html'],
                                   'section_key': 'samstat_summary',
                                   'native_fields': ['2.2.3 mappingtableval[1 or3][4] native per-mate Total',
                                                     '2.2.3 paired overview reads exact integer or (exact:N) '
                                                     'suffix',
                                                     '2.5.0 strip Reads/Reads(R1+R2): exact sublabel or unscaled '
                                                     'count',
                                                     '2.5.0 no-reads banner with explicit SAM/BAM mode',
                                                     'caller-failure heading: failed/null sentinel only'],
                                   'units': ['alignment_records'],
                                   'axis_kinds': ['none'],
                                   'population_keys': ['samstat_report_records',
                                                       'samstat_mapq_ge30',
                                                       'samstat_mapq_10_29',
                                                       'samstat_mapq_0_9',
                                                       'samstat_unmapped',
                                                       'samstat_report_sequences'],
                                   'meaning': 'observed_count',
                                   'precision': 'exact_for_retained_population',
                                   'value_domain': 'nonnegative_integer',
                                   'interpretation': 'Exact contributing alignment-record total explicitly '
                                                     'printed by the recognized version.2.2.3 excludes secondary '
                                                     'but includes supplementary;2.5.0 excludes both. Report-wide '
                                                     'and per-mate totals are repeated/overlapping native '
                                                     'populations, not independently summable. Caller failure has '
                                                     'null measurement.',
                                   'denominator': None,
                                   'coordinates': 'Bin order ge30,10_29,0_9,unmapped,Total. ge30 includes MAPQ '
                                                  '255. MAPQ is not reference coordinate. none none none',
                                   'uncertainty': 'not reported Original-input completeness is unknown '
                                                  'independently of HTML transfer completeness',
                                   'missing_behavior': 'Missing column is absent, not a zero-filled mate. '
                                                       'Independent complete columns survive truncated HTML. '
                                                       'Bases n/a with absent sequence is not zero observed '
                                                       'bases. Empty file native banner establishes 0 '
                                                       'contributing records but no ordinary sequence/quality '
                                                       'summaries. Caller stub: failed measurement null; '
                                                       'supported HTML with truncated structural section: '
                                                       'preserve independent cells and typed partial. Exit 0 '
                                                       'alone does not prove full consumption. Overview is '
                                                       'conditional on paired records; absence does not imply '
                                                       'zero. Native per-mate table totals remain separately '
                                                       'retained.',
                                   'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                      'PARSER_CALCULATOR_PORTS_002.md',
                                   'allowed_precisions': ['exact_for_retained_population', 'not_reported'],
                                   'source_field_ids': ['legacy_mapping_counts',
                                                        'modern_total_counts',
                                                        'partial_and_failure',
                                                        'legacy_report_wide_total'],
                                   'native_precision_description': 'exact integer token Exact integer when '
                                                                   'unscaled main token or exact comma-separated '
                                                                   'span.sub; preserve separate SI display with '
                                                                   'native_rounded Retain whatever complete '
                                                                   'numeric tokens exist; no recovery from '
                                                                   'nonexistent or truncated fields exact '
                                                                   'integer, from exact suffix when main display '
                                                                   'is rounded',
                                   'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                       'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                       'samstat_2_2_3/src/report/stat_report.c',
                                                       'samstat/src/collect/collect.c',
                                                       'samstat/src/htsinterface/htsglue.c',
                                                       'samstat/src/report/stat_report.c',
                                                       'caller:lib/fastq_utils.py:run_alignment'],
                                   'qualifications': ['Native labels MAPQ gt 30 and MAPQ lt 30 are misleading: '
                                                      'exact integer boundaries come from pinned '
                                                      'get_mapqual_bins.',
                                                      'The report has no query-name identity or reference '
                                                      'dictionary; counts are not deduplicated reads or pairs.',
                                                      'Use exact sublabel for arithmetic; do not reconstruct '
                                                      'exact count from SI main display alone.',
                                                      'Legacy peeking operates after whole default 10000-record '
                                                      'chunks. Modern peeking enforces exact record limit. '
                                                      'Neither prefix is a random sample.',
                                                      'Caller labels every CalledProcessError a segfault; '
                                                      'retained code 1 must not be rewritten as SIGSEGV.',
                                                      'Do not synthesize missing combined mapping-bin rows in the '
                                                      'parser.']},
 'samstat_base_A_count': {'metric': 'samstat_base_A_count',
                          'formats': ['samstat_html_2_2_3'],
                          'section_key': 'samstat_base_start',
                          'native_fields': ['2.2.3 bc_R{mate}_{bin}_A.y / end / norm variants; unclustered '
                                            'integer'],
                          'units': ['bases'],
                          'axis_kinds': ['base_closed_1',
                                         'base_offset_from_end_0',
                                         'read_fraction_bin_0_100',
                                         'native_label'],
                          'population_keys': ['samstat_report_records',
                                              'samstat_mapq_ge30',
                                              'samstat_mapq_10_29',
                                              'samstat_mapq_0_9',
                                              'samstat_unmapped',
                                              'samstat_report_sequences'],
                          'meaning': 'observed_count',
                          'precision': 'exact_for_retained_population',
                          'value_domain': 'nonnegative_integer',
                          'interpretation': 'Bases contributed by the named record stratum at the named '
                                            'coordinate, in sequenced orientation; variable coverage and missing '
                                            'sequences retained',
                          'denominator': 'No numeric denominator emitted per base; sum of emitted symbol counts '
                                         'only if all symbol series for that cell are demonstrably represented',
                          'coordinates': 'Default unclustered x labels 1..length. SAM/BAM default excludes soft '
                                         'clips then positions in trimmed sequence; reverse records are '
                                         'reoriented. End plots use full sequence from its end despite caption. '
                                         'Norm assigns floor(100*p/trimmed_length), displayed index+1. Native '
                                         'label retained.',
                          'uncertainty': 'not reported',
                          'missing_behavior': 'Omitted all-zero groups/series and malformed arrays remain '
                                              'explicit absence; parser must not fabricate omitted zeros.',
                          'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                          'source_field_ids': ['legacy_base_position_counts'],
                          'native_precision_description': 'exact integer tokens only for unclustered axes',
                          'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                              'samstat_2_2_3/src/htsinterface/htsglue.c',
                                              'samstat_2_2_3/src/report/stat_report.c',
                                              'samstat_2_2_3/src/plot/plot.c',
                                              'samstat_2_2_3/src/plot/plot_interval.c',
                                              'samstat_2_2_3/src/plot/plot_group.c'],
                          'qualifications': []},
 'samstat_base_A_rounded_bin_mean': {'metric': 'samstat_base_A_rounded_bin_mean',
                                     'formats': ['samstat_html_2_2_3'],
                                     'section_key': 'samstat_base_start',
                                     'native_fields': ['2.2.3 bc_R{mate}_{bin}_A.y / end / norm variants; '
                                                       'clustered rounded native mean'],
                                     'units': ['scaled_native_count'],
                                     'axis_kinds': ['native_label'],
                                     'population_keys': ['samstat_report_records',
                                                         'samstat_mapq_ge30',
                                                         'samstat_mapq_10_29',
                                                         'samstat_mapq_0_9',
                                                         'samstat_unmapped',
                                                         'samstat_report_sequences'],
                                     'meaning': 'native_normalized',
                                     'precision': 'native_rounded',
                                     'value_domain': 'nonnegative_integer',
                                     'interpretation': 'Same stratum as legacy_base_position_counts, but several '
                                                       'positions summarized Clustered native rounded mean per '
                                                       'allocated position; never an exact cardinality.',
                                     'denominator': 'Number of allocated positions in native cluster, not records '
                                                    'or event count. Original unclustered counts are not '
                                                    'recoverable.',
                                     'coordinates': 'For 300-bp example x singleton labels start 0, then 250-255 '
                                                    'etc. Textual cluster labels are not reliable closed interval '
                                                    'endpoints. Use native_label axis with bounds null, preserve '
                                                    'exact label.',
                                     'uncertainty': 'No variance or rounding interval emitted',
                                     'missing_behavior': 'Do not recover total bases by multiplying the displayed '
                                                         'value by a guessed width.',
                                     'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                        'PARSER_CALCULATOR_PORTS_002.md',
                                     'source_field_ids': ['legacy_clustered_base_values'],
                                     'native_precision_description': 'native_rounded: integer round(sum(position '
                                                                     'counts)/number positions assigned to '
                                                                     'cluster)',
                                     'source_evidence': ['samstat_2_2_3/src/plot/plot.c',
                                                         'samstat_2_2_3/src/plot/plot_interval.c',
                                                         'samstat_2_2_3/src/plot/plot_group.c'],
                                     'qualifications': ['Source clustering can include an allocated terminal '
                                                        'empty position. Even integer-looking values may be '
                                                        'rounded averages.']},
 'samstat_base_C_count': {'metric': 'samstat_base_C_count',
                          'formats': ['samstat_html_2_2_3'],
                          'section_key': 'samstat_base_start',
                          'native_fields': ['2.2.3 bc_R{mate}_{bin}_C.y / end / norm variants; unclustered '
                                            'integer'],
                          'units': ['bases'],
                          'axis_kinds': ['base_closed_1',
                                         'base_offset_from_end_0',
                                         'read_fraction_bin_0_100',
                                         'native_label'],
                          'population_keys': ['samstat_report_records',
                                              'samstat_mapq_ge30',
                                              'samstat_mapq_10_29',
                                              'samstat_mapq_0_9',
                                              'samstat_unmapped',
                                              'samstat_report_sequences'],
                          'meaning': 'observed_count',
                          'precision': 'exact_for_retained_population',
                          'value_domain': 'nonnegative_integer',
                          'interpretation': 'Bases contributed by the named record stratum at the named '
                                            'coordinate, in sequenced orientation; variable coverage and missing '
                                            'sequences retained',
                          'denominator': 'No numeric denominator emitted per base; sum of emitted symbol counts '
                                         'only if all symbol series for that cell are demonstrably represented',
                          'coordinates': 'Default unclustered x labels 1..length. SAM/BAM default excludes soft '
                                         'clips then positions in trimmed sequence; reverse records are '
                                         'reoriented. End plots use full sequence from its end despite caption. '
                                         'Norm assigns floor(100*p/trimmed_length), displayed index+1. Native '
                                         'label retained.',
                          'uncertainty': 'not reported',
                          'missing_behavior': 'Omitted all-zero groups/series and malformed arrays remain '
                                              'explicit absence; parser must not fabricate omitted zeros.',
                          'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                          'source_field_ids': ['legacy_base_position_counts'],
                          'native_precision_description': 'exact integer tokens only for unclustered axes',
                          'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                              'samstat_2_2_3/src/htsinterface/htsglue.c',
                                              'samstat_2_2_3/src/report/stat_report.c',
                                              'samstat_2_2_3/src/plot/plot.c',
                                              'samstat_2_2_3/src/plot/plot_interval.c',
                                              'samstat_2_2_3/src/plot/plot_group.c'],
                          'qualifications': []},
 'samstat_base_C_rounded_bin_mean': {'metric': 'samstat_base_C_rounded_bin_mean',
                                     'formats': ['samstat_html_2_2_3'],
                                     'section_key': 'samstat_base_start',
                                     'native_fields': ['2.2.3 bc_R{mate}_{bin}_C.y / end / norm variants; '
                                                       'clustered rounded native mean'],
                                     'units': ['scaled_native_count'],
                                     'axis_kinds': ['native_label'],
                                     'population_keys': ['samstat_report_records',
                                                         'samstat_mapq_ge30',
                                                         'samstat_mapq_10_29',
                                                         'samstat_mapq_0_9',
                                                         'samstat_unmapped',
                                                         'samstat_report_sequences'],
                                     'meaning': 'native_normalized',
                                     'precision': 'native_rounded',
                                     'value_domain': 'nonnegative_integer',
                                     'interpretation': 'Same stratum as legacy_base_position_counts, but several '
                                                       'positions summarized Clustered native rounded mean per '
                                                       'allocated position; never an exact cardinality.',
                                     'denominator': 'Number of allocated positions in native cluster, not records '
                                                    'or event count. Original unclustered counts are not '
                                                    'recoverable.',
                                     'coordinates': 'For 300-bp example x singleton labels start 0, then 250-255 '
                                                    'etc. Textual cluster labels are not reliable closed interval '
                                                    'endpoints. Use native_label axis with bounds null, preserve '
                                                    'exact label.',
                                     'uncertainty': 'No variance or rounding interval emitted',
                                     'missing_behavior': 'Do not recover total bases by multiplying the displayed '
                                                         'value by a guessed width.',
                                     'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                        'PARSER_CALCULATOR_PORTS_002.md',
                                     'source_field_ids': ['legacy_clustered_base_values'],
                                     'native_precision_description': 'native_rounded: integer round(sum(position '
                                                                     'counts)/number positions assigned to '
                                                                     'cluster)',
                                     'source_evidence': ['samstat_2_2_3/src/plot/plot.c',
                                                         'samstat_2_2_3/src/plot/plot_interval.c',
                                                         'samstat_2_2_3/src/plot/plot_group.c'],
                                     'qualifications': ['Source clustering can include an allocated terminal '
                                                        'empty position. Even integer-looking values may be '
                                                        'rounded averages.']},
 'samstat_base_G_count': {'metric': 'samstat_base_G_count',
                          'formats': ['samstat_html_2_2_3'],
                          'section_key': 'samstat_base_start',
                          'native_fields': ['2.2.3 bc_R{mate}_{bin}_G.y / end / norm variants; unclustered '
                                            'integer'],
                          'units': ['bases'],
                          'axis_kinds': ['base_closed_1',
                                         'base_offset_from_end_0',
                                         'read_fraction_bin_0_100',
                                         'native_label'],
                          'population_keys': ['samstat_report_records',
                                              'samstat_mapq_ge30',
                                              'samstat_mapq_10_29',
                                              'samstat_mapq_0_9',
                                              'samstat_unmapped',
                                              'samstat_report_sequences'],
                          'meaning': 'observed_count',
                          'precision': 'exact_for_retained_population',
                          'value_domain': 'nonnegative_integer',
                          'interpretation': 'Bases contributed by the named record stratum at the named '
                                            'coordinate, in sequenced orientation; variable coverage and missing '
                                            'sequences retained',
                          'denominator': 'No numeric denominator emitted per base; sum of emitted symbol counts '
                                         'only if all symbol series for that cell are demonstrably represented',
                          'coordinates': 'Default unclustered x labels 1..length. SAM/BAM default excludes soft '
                                         'clips then positions in trimmed sequence; reverse records are '
                                         'reoriented. End plots use full sequence from its end despite caption. '
                                         'Norm assigns floor(100*p/trimmed_length), displayed index+1. Native '
                                         'label retained.',
                          'uncertainty': 'not reported',
                          'missing_behavior': 'Omitted all-zero groups/series and malformed arrays remain '
                                              'explicit absence; parser must not fabricate omitted zeros.',
                          'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                          'source_field_ids': ['legacy_base_position_counts'],
                          'native_precision_description': 'exact integer tokens only for unclustered axes',
                          'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                              'samstat_2_2_3/src/htsinterface/htsglue.c',
                                              'samstat_2_2_3/src/report/stat_report.c',
                                              'samstat_2_2_3/src/plot/plot.c',
                                              'samstat_2_2_3/src/plot/plot_interval.c',
                                              'samstat_2_2_3/src/plot/plot_group.c'],
                          'qualifications': []},
 'samstat_base_G_rounded_bin_mean': {'metric': 'samstat_base_G_rounded_bin_mean',
                                     'formats': ['samstat_html_2_2_3'],
                                     'section_key': 'samstat_base_start',
                                     'native_fields': ['2.2.3 bc_R{mate}_{bin}_G.y / end / norm variants; '
                                                       'clustered rounded native mean'],
                                     'units': ['scaled_native_count'],
                                     'axis_kinds': ['native_label'],
                                     'population_keys': ['samstat_report_records',
                                                         'samstat_mapq_ge30',
                                                         'samstat_mapq_10_29',
                                                         'samstat_mapq_0_9',
                                                         'samstat_unmapped',
                                                         'samstat_report_sequences'],
                                     'meaning': 'native_normalized',
                                     'precision': 'native_rounded',
                                     'value_domain': 'nonnegative_integer',
                                     'interpretation': 'Same stratum as legacy_base_position_counts, but several '
                                                       'positions summarized Clustered native rounded mean per '
                                                       'allocated position; never an exact cardinality.',
                                     'denominator': 'Number of allocated positions in native cluster, not records '
                                                    'or event count. Original unclustered counts are not '
                                                    'recoverable.',
                                     'coordinates': 'For 300-bp example x singleton labels start 0, then 250-255 '
                                                    'etc. Textual cluster labels are not reliable closed interval '
                                                    'endpoints. Use native_label axis with bounds null, preserve '
                                                    'exact label.',
                                     'uncertainty': 'No variance or rounding interval emitted',
                                     'missing_behavior': 'Do not recover total bases by multiplying the displayed '
                                                         'value by a guessed width.',
                                     'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                        'PARSER_CALCULATOR_PORTS_002.md',
                                     'source_field_ids': ['legacy_clustered_base_values'],
                                     'native_precision_description': 'native_rounded: integer round(sum(position '
                                                                     'counts)/number positions assigned to '
                                                                     'cluster)',
                                     'source_evidence': ['samstat_2_2_3/src/plot/plot.c',
                                                         'samstat_2_2_3/src/plot/plot_interval.c',
                                                         'samstat_2_2_3/src/plot/plot_group.c'],
                                     'qualifications': ['Source clustering can include an allocated terminal '
                                                        'empty position. Even integer-looking values may be '
                                                        'rounded averages.']},
 'samstat_base_N_count': {'metric': 'samstat_base_N_count',
                          'formats': ['samstat_html_2_2_3'],
                          'section_key': 'samstat_base_start',
                          'native_fields': ['2.2.3 bc_R{mate}_{bin}_N.y / end / norm variants; unclustered '
                                            'integer'],
                          'units': ['bases'],
                          'axis_kinds': ['base_closed_1',
                                         'base_offset_from_end_0',
                                         'read_fraction_bin_0_100',
                                         'native_label'],
                          'population_keys': ['samstat_report_records',
                                              'samstat_mapq_ge30',
                                              'samstat_mapq_10_29',
                                              'samstat_mapq_0_9',
                                              'samstat_unmapped',
                                              'samstat_report_sequences'],
                          'meaning': 'observed_count',
                          'precision': 'exact_for_retained_population',
                          'value_domain': 'nonnegative_integer',
                          'interpretation': 'Bases contributed by the named record stratum at the named '
                                            'coordinate, in sequenced orientation; variable coverage and missing '
                                            'sequences retained',
                          'denominator': 'No numeric denominator emitted per base; sum of emitted symbol counts '
                                         'only if all symbol series for that cell are demonstrably represented',
                          'coordinates': 'Default unclustered x labels 1..length. SAM/BAM default excludes soft '
                                         'clips then positions in trimmed sequence; reverse records are '
                                         'reoriented. End plots use full sequence from its end despite caption. '
                                         'Norm assigns floor(100*p/trimmed_length), displayed index+1. Native '
                                         'label retained.',
                          'uncertainty': 'not reported',
                          'missing_behavior': 'Omitted all-zero groups/series and malformed arrays remain '
                                              'explicit absence; parser must not fabricate omitted zeros.',
                          'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                          'source_field_ids': ['legacy_base_position_counts'],
                          'native_precision_description': 'exact integer tokens only for unclustered axes',
                          'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                              'samstat_2_2_3/src/htsinterface/htsglue.c',
                                              'samstat_2_2_3/src/report/stat_report.c',
                                              'samstat_2_2_3/src/plot/plot.c',
                                              'samstat_2_2_3/src/plot/plot_interval.c',
                                              'samstat_2_2_3/src/plot/plot_group.c'],
                          'qualifications': []},
 'samstat_base_N_rounded_bin_mean': {'metric': 'samstat_base_N_rounded_bin_mean',
                                     'formats': ['samstat_html_2_2_3'],
                                     'section_key': 'samstat_base_start',
                                     'native_fields': ['2.2.3 bc_R{mate}_{bin}_N.y / end / norm variants; '
                                                       'clustered rounded native mean'],
                                     'units': ['scaled_native_count'],
                                     'axis_kinds': ['native_label'],
                                     'population_keys': ['samstat_report_records',
                                                         'samstat_mapq_ge30',
                                                         'samstat_mapq_10_29',
                                                         'samstat_mapq_0_9',
                                                         'samstat_unmapped',
                                                         'samstat_report_sequences'],
                                     'meaning': 'native_normalized',
                                     'precision': 'native_rounded',
                                     'value_domain': 'nonnegative_integer',
                                     'interpretation': 'Same stratum as legacy_base_position_counts, but several '
                                                       'positions summarized Clustered native rounded mean per '
                                                       'allocated position; never an exact cardinality.',
                                     'denominator': 'Number of allocated positions in native cluster, not records '
                                                    'or event count. Original unclustered counts are not '
                                                    'recoverable.',
                                     'coordinates': 'For 300-bp example x singleton labels start 0, then 250-255 '
                                                    'etc. Textual cluster labels are not reliable closed interval '
                                                    'endpoints. Use native_label axis with bounds null, preserve '
                                                    'exact label.',
                                     'uncertainty': 'No variance or rounding interval emitted',
                                     'missing_behavior': 'Do not recover total bases by multiplying the displayed '
                                                         'value by a guessed width.',
                                     'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                        'PARSER_CALCULATOR_PORTS_002.md',
                                     'source_field_ids': ['legacy_clustered_base_values'],
                                     'native_precision_description': 'native_rounded: integer round(sum(position '
                                                                     'counts)/number positions assigned to '
                                                                     'cluster)',
                                     'source_evidence': ['samstat_2_2_3/src/plot/plot.c',
                                                         'samstat_2_2_3/src/plot/plot_interval.c',
                                                         'samstat_2_2_3/src/plot/plot_group.c'],
                                     'qualifications': ['Source clustering can include an allocated terminal '
                                                        'empty position. Even integer-looking values may be '
                                                        'rounded averages.']},
 'samstat_base_T_count': {'metric': 'samstat_base_T_count',
                          'formats': ['samstat_html_2_2_3'],
                          'section_key': 'samstat_base_start',
                          'native_fields': ['2.2.3 bc_R{mate}_{bin}_T.y / end / norm variants; unclustered '
                                            'integer'],
                          'units': ['bases'],
                          'axis_kinds': ['base_closed_1',
                                         'base_offset_from_end_0',
                                         'read_fraction_bin_0_100',
                                         'native_label'],
                          'population_keys': ['samstat_report_records',
                                              'samstat_mapq_ge30',
                                              'samstat_mapq_10_29',
                                              'samstat_mapq_0_9',
                                              'samstat_unmapped',
                                              'samstat_report_sequences'],
                          'meaning': 'observed_count',
                          'precision': 'exact_for_retained_population',
                          'value_domain': 'nonnegative_integer',
                          'interpretation': 'Bases contributed by the named record stratum at the named '
                                            'coordinate, in sequenced orientation; variable coverage and missing '
                                            'sequences retained',
                          'denominator': 'No numeric denominator emitted per base; sum of emitted symbol counts '
                                         'only if all symbol series for that cell are demonstrably represented',
                          'coordinates': 'Default unclustered x labels 1..length. SAM/BAM default excludes soft '
                                         'clips then positions in trimmed sequence; reverse records are '
                                         'reoriented. End plots use full sequence from its end despite caption. '
                                         'Norm assigns floor(100*p/trimmed_length), displayed index+1. Native '
                                         'label retained.',
                          'uncertainty': 'not reported',
                          'missing_behavior': 'Omitted all-zero groups/series and malformed arrays remain '
                                              'explicit absence; parser must not fabricate omitted zeros.',
                          'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                          'source_field_ids': ['legacy_base_position_counts'],
                          'native_precision_description': 'exact integer tokens only for unclustered axes',
                          'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                              'samstat_2_2_3/src/htsinterface/htsglue.c',
                                              'samstat_2_2_3/src/report/stat_report.c',
                                              'samstat_2_2_3/src/plot/plot.c',
                                              'samstat_2_2_3/src/plot/plot_interval.c',
                                              'samstat_2_2_3/src/plot/plot_group.c'],
                          'qualifications': []},
 'samstat_base_T_rounded_bin_mean': {'metric': 'samstat_base_T_rounded_bin_mean',
                                     'formats': ['samstat_html_2_2_3'],
                                     'section_key': 'samstat_base_start',
                                     'native_fields': ['2.2.3 bc_R{mate}_{bin}_T.y / end / norm variants; '
                                                       'clustered rounded native mean'],
                                     'units': ['scaled_native_count'],
                                     'axis_kinds': ['native_label'],
                                     'population_keys': ['samstat_report_records',
                                                         'samstat_mapq_ge30',
                                                         'samstat_mapq_10_29',
                                                         'samstat_mapq_0_9',
                                                         'samstat_unmapped',
                                                         'samstat_report_sequences'],
                                     'meaning': 'native_normalized',
                                     'precision': 'native_rounded',
                                     'value_domain': 'nonnegative_integer',
                                     'interpretation': 'Same stratum as legacy_base_position_counts, but several '
                                                       'positions summarized Clustered native rounded mean per '
                                                       'allocated position; never an exact cardinality.',
                                     'denominator': 'Number of allocated positions in native cluster, not records '
                                                    'or event count. Original unclustered counts are not '
                                                    'recoverable.',
                                     'coordinates': 'For 300-bp example x singleton labels start 0, then 250-255 '
                                                    'etc. Textual cluster labels are not reliable closed interval '
                                                    'endpoints. Use native_label axis with bounds null, preserve '
                                                    'exact label.',
                                     'uncertainty': 'No variance or rounding interval emitted',
                                     'missing_behavior': 'Do not recover total bases by multiplying the displayed '
                                                         'value by a guessed width.',
                                     'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                        'PARSER_CALCULATOR_PORTS_002.md',
                                     'source_field_ids': ['legacy_clustered_base_values'],
                                     'native_precision_description': 'native_rounded: integer round(sum(position '
                                                                     'counts)/number positions assigned to '
                                                                     'cluster)',
                                     'source_evidence': ['samstat_2_2_3/src/plot/plot.c',
                                                         'samstat_2_2_3/src/plot/plot_interval.c',
                                                         'samstat_2_2_3/src/plot/plot_group.c'],
                                     'qualifications': ['Source clustering can include an allocated terminal '
                                                        'empty position. Even integer-looking values may be '
                                                        'rounded averages.']},
 'samstat_beyond_axis_percent': {'metric': 'samstat_beyond_axis_percent',
                                 'formats': ['samstat_html_2_5_0'],
                                 'section_key': 'samstat_notes',
                                 'native_fields': ['2.5.0 notes X% of bases lie beyond position1000: X native '
                                                   'rounded percent'],
                                 'units': ['percent'],
                                 'axis_kinds': ['none'],
                                 'population_keys': ['samstat_report_records',
                                                     'samstat_mapq_ge30',
                                                     'samstat_mapq_10_29',
                                                     'samstat_mapq_0_9',
                                                     'samstat_unmapped',
                                                     'samstat_report_sequences'],
                                 'meaning': 'native_normalized',
                                 'precision': 'native_rounded',
                                 'value_domain': 'number_0_100',
                                 'interpretation': 'Bases used in positional plots; clipped/axis conventions '
                                                   'follow native plot collection',
                                 'denominator': 'beyond/(beyond+in_axis)*100, counts not persisted in HTML',
                                 'coordinates': 'Beyond short-layout position axis, not genome coordinates',
                                 'uncertainty': 'No statistical uncertainty; display censoring only',
                                 'missing_behavior': 'Absent note gives no observed count or fraction; do not '
                                                     'assume zero.',
                                 'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                 'source_field_ids': ['modern_beyond_axis'],
                                 'native_precision_description': 'one decimal rounded value or explicit strict '
                                                                 'upper bound <0.1; bound metric records 0.1 with '
                                                                 'native token and strictness fixed by metric '
                                                                 'definition',
                                 'source_evidence': ['samstat/src/collect/collect.c',
                                                     'samstat/src/htsinterface/htsglue.c',
                                                     'samstat/src/report/stat_report.c'],
                                 'qualifications': ['Source established; no positive beyond-axis native example '
                                                    'was run in this workload.']},
 'samstat_beyond_axis_percent_upper_bound': {'metric': 'samstat_beyond_axis_percent_upper_bound',
                                             'formats': ['samstat_html_2_5_0'],
                                             'section_key': 'samstat_notes',
                                             'native_fields': ['2.5.0 notes &lt;0.1% of bases lie beyond '
                                                               'position1000: strict upper bound0.1'],
                                             'units': ['percent'],
                                             'axis_kinds': ['none'],
                                             'population_keys': ['samstat_report_records',
                                                                 'samstat_mapq_ge30',
                                                                 'samstat_mapq_10_29',
                                                                 'samstat_mapq_0_9',
                                                                 'samstat_unmapped',
                                                                 'samstat_report_sequences'],
                                             'meaning': 'native_normalized',
                                             'precision': 'native_rounded',
                                             'value_domain': 'number_0_100',
                                             'interpretation': 'Bases used in positional plots; clipped/axis '
                                                               'conventions follow native plot collection Value '
                                                               'is a strict upper bound: actual percentage is '
                                                               'less than value.',
                                             'denominator': 'beyond/(beyond+in_axis)*100, counts not persisted in '
                                                            'HTML',
                                             'coordinates': 'Beyond short-layout position axis, not genome '
                                                            'coordinates',
                                             'uncertainty': 'No statistical uncertainty; display censoring only',
                                             'missing_behavior': 'Absent note gives no observed count or '
                                                                 'fraction; do not assume zero.',
                                             'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                                'PARSER_CALCULATOR_PORTS_002.md',
                                             'source_field_ids': ['modern_beyond_axis'],
                                             'native_precision_description': 'one decimal rounded value or '
                                                                             'explicit strict upper bound <0.1; '
                                                                             'bound metric records 0.1 with '
                                                                             'native token and strictness fixed '
                                                                             'by metric definition',
                                             'source_evidence': ['samstat/src/collect/collect.c',
                                                                 'samstat/src/htsinterface/htsglue.c',
                                                                 'samstat/src/report/stat_report.c'],
                                             'qualifications': ['Source established; no positive beyond-axis '
                                                                'native example was run in this workload.']},
 'samstat_deletion_open_count': {'metric': 'samstat_deletion_open_count',
                                 'formats': ['samstat_html_2_2_3'],
                                 'section_key': 'samstat_deletion',
                                 'native_fields': ['2.2.3 del_R{mate}__{bin}.y; unclustered gap-opening integer'],
                                 'units': ['events'],
                                 'axis_kinds': ['base_closed_1',
                                                'base_offset_from_end_0',
                                                'read_fraction_bin_0_100',
                                                'native_label'],
                                 'population_keys': ['samstat_report_records',
                                                     'samstat_mapq_ge30',
                                                     'samstat_mapq_10_29',
                                                     'samstat_mapq_0_9',
                                                     'samstat_unmapped',
                                                     'samstat_report_sequences'],
                                 'meaning': 'observed_count',
                                 'precision': 'exact_for_retained_population',
                                 'value_domain': 'nonnegative_integer',
                                 'interpretation': 'Error events reconstructed by native CIGAR/MD processing for '
                                                   'named mate/MAPQ stratum; mismatch base labels describe read '
                                                   'bases',
                                 'denominator': 'No coverage denominator or native error rate emitted; indel '
                                                'values count gap openings, not bases in gaps',
                                 'coordinates': 'Native read position after native orientation/soft-clip '
                                                'handling, not genomic coordinate. Preserve x unchanged and the '
                                                'soft-clip defect qualification.',
                                 'uncertainty': 'not reported',
                                 'missing_behavior': 'Absent MD yields no known mismatch information; zero '
                                                     'displayed mismatch is not proof of error-free alignment.',
                                 'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                 'source_field_ids': ['legacy_alignment_errors'],
                                 'native_precision_description': 'exact unclustered integer token; clustered '
                                                                 'variants must use '
                                                                 'native_normalized/native_rounded metric suffix '
                                                                 '_rounded_bin_mean',
                                 'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                     'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                     'samstat_2_2_3/src/report/stat_report.c',
                                                     'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                     'samstat_2_2_3/src/plot/plot.c',
                                                     'samstat_2_2_3/src/plot/plot_interval.c',
                                                     'samstat_2_2_3/src/plot/plot_group.c'],
                                 'qualifications': ['Pinned parse_alignment advances sequence cursor by one for '
                                                    'any S operation, not its length; native reconstructed '
                                                    'mismatch assignment after multi-base soft clipping can be '
                                                    'wrong. Preserve native output; no silent correction.']},
 'samstat_error_probability_mean_phred': {'metric': 'samstat_error_probability_mean_phred',
                                          'formats': ['samstat_html_2_5_0'],
                                          'section_key': 'samstat_summary',
                                          'native_fields': ['strip Mean Q'],
                                          'units': ['phred'],
                                          'axis_kinds': ['none'],
                                          'population_keys': ['samstat_report_records',
                                                              'samstat_mapq_ge30',
                                                              'samstat_mapq_10_29',
                                                              'samstat_mapq_0_9',
                                                              'samstat_unmapped',
                                                              'samstat_report_sequences'],
                                          'meaning': 'native_normalized',
                                          'precision': 'native_rounded',
                                          'value_domain': 'nonnegative_number',
                                          'interpretation': 'All bases with usable qualities in all included '
                                                            'primary/FASTX records, including soft clips; missing '
                                                            'QUAL bases excluded',
                                          'denominator': '-10*log10(sum(round(2^30*10^(-min(Q,93)/10)))/(n*2^30)), '
                                                         'with native zero-error saturation at Q93',
                                          'coordinates': 'none',
                                          'uncertainty': 'No variance, SEM, confidence interval or quality-base '
                                                         'count emitted in HTML',
                                          'missing_behavior': 'No quality-bearing bases -> card omitted, '
                                                              'not_measured, not zero.',
                                          'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                             'PARSER_CALCULATOR_PORTS_002.md',
                                          'source_field_ids': ['modern_mean_quality'],
                                          'native_precision_description': 'native_rounded to one decimal; native '
                                                                          'fixed-point error table adds finite '
                                                                          'numerical approximation',
                                          'source_evidence': ['samstat/src/collect/collect.c',
                                                              'samstat/src/htsinterface/htsglue.c',
                                                              'samstat/src/report/stat_report.c'],
                                          'qualifications': ['Different statistic from arithmetic mean Phred; two '
                                                             'Q0/Q40 bases give 3.0 here versus legacy mean '
                                                             '20.000000.']},
 'samstat_gap_compressed_median_identity_percent': {'metric': 'samstat_gap_compressed_median_identity_percent',
                                                    'formats': ['samstat_html_2_5_0'],
                                                    'section_key': 'samstat_identity',
                                                    'native_fields': ['strip Median identity'],
                                                    'units': ['percent'],
                                                    'axis_kinds': ['none'],
                                                    'population_keys': ['samstat_report_records',
                                                                        'samstat_mapq_ge30',
                                                                        'samstat_mapq_10_29',
                                                                        'samstat_mapq_0_9',
                                                                        'samstat_unmapped',
                                                                        'samstat_report_sequences'],
                                                    'meaning': 'native_estimate',
                                                    'precision': 'native_estimator',
                                                    'value_domain': 'number_0_100',
                                                    'interpretation': 'Mapped primary records where native '
                                                                      'identity is computable from NM plus CIGAR '
                                                                      'or explicit X operations; MD alone does '
                                                                      'not establish identity',
                                                    'denominator': 'Per record (aligned M/X/= bases - '
                                                                   'mismatches)/(aligned M/X/= bases + '
                                                                   'insertion-open events + deletion-open '
                                                                   'events), then native median; not global '
                                                                   'matching bases / all alignment columns',
                                                    'coordinates': 'No residue/reference correspondence retained; '
                                                                   'gap openings differ from gap lengths',
                                                    'uncertainty': 'No interval; empirical binned median only',
                                                    'missing_behavior': 'n/a if no calculable identities; '
                                                                        'incompatible NM/CIGAR treated '
                                                                        'unavailable by producer.',
                                                    'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                                       'PARSER_CALCULATOR_PORTS_002.md',
                                                    'source_field_ids': ['modern_identity'],
                                                    'native_precision_description': 'native_estimator: lower '
                                                                                    'median of 0.1 '
                                                                                    'percentage-point bins; shown '
                                                                                    'one decimal',
                                                    'source_evidence': ['samstat/src/collect/collect.c',
                                                                        'samstat/src/htsinterface/htsglue.c',
                                                                        'samstat/src/report/stat_report.c'],
                                                    'qualifications': []},
 'samstat_identity_unavailable_record_count': {'metric': 'samstat_identity_unavailable_record_count',
                                               'formats': ['samstat_html_2_5_0'],
                                               'section_key': 'samstat_notes',
                                               'native_fields': ['2.5.0 notes Identity unavailable for X of Y '
                                                                 'mapped reads: X'],
                                               'units': ['alignment_records'],
                                               'axis_kinds': ['none'],
                                               'population_keys': ['samstat_report_records',
                                                                   'samstat_mapq_ge30',
                                                                   'samstat_mapq_10_29',
                                                                   'samstat_mapq_0_9',
                                                                   'samstat_unmapped',
                                                                   'samstat_report_sequences'],
                                               'meaning': 'observed_count',
                                               'precision': 'exact_for_retained_population',
                                               'value_domain': 'nonnegative_integer',
                                               'interpretation': 'Numerator is the named unavailable/excluded '
                                                                 'population. Note denominator is mapped primary '
                                                                 'report records. Display threshold 50 is '
                                                                 'producer configuration, not a measurement. '
                                                                 'Excluded secondary/supplementary records are '
                                                                 'not contributors.',
                                               'denominator': 'Named note denominator only, not all primary '
                                                              'records for missing-data fractions',
                                               'coordinates': 'none',
                                               'uncertainty': 'not reported',
                                               'missing_behavior': 'Conditional note absence is not parsed as '
                                                                   'observed zero; preserve unsupported/absent '
                                                                   'section if not recognizable.',
                                               'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                                  'PARSER_CALCULATOR_PORTS_002.md',
                                               'source_field_ids': ['modern_data_coverage_notes'],
                                               'native_precision_description': 'exact comma-separated integer '
                                                                               'tokens',
                                               'source_evidence': ['samstat/src/collect/collect.c',
                                                                   'samstat/src/htsinterface/htsglue.c',
                                                                   'samstat/src/report/stat_report.c',
                                                                   'samstat/src/report/report_help.c'],
                                               'qualifications': []},
 'samstat_insertion_open_count': {'metric': 'samstat_insertion_open_count',
                                  'formats': ['samstat_html_2_2_3'],
                                  'section_key': 'samstat_insertion',
                                  'native_fields': ['2.2.3 ins_R{mate}__{bin}.y; unclustered gap-opening integer'],
                                  'units': ['events'],
                                  'axis_kinds': ['base_closed_1',
                                                 'base_offset_from_end_0',
                                                 'read_fraction_bin_0_100',
                                                 'native_label'],
                                  'population_keys': ['samstat_report_records',
                                                      'samstat_mapq_ge30',
                                                      'samstat_mapq_10_29',
                                                      'samstat_mapq_0_9',
                                                      'samstat_unmapped',
                                                      'samstat_report_sequences'],
                                  'meaning': 'observed_count',
                                  'precision': 'exact_for_retained_population',
                                  'value_domain': 'nonnegative_integer',
                                  'interpretation': 'Error events reconstructed by native CIGAR/MD processing for '
                                                    'named mate/MAPQ stratum; mismatch base labels describe read '
                                                    'bases',
                                  'denominator': 'No coverage denominator or native error rate emitted; indel '
                                                 'values count gap openings, not bases in gaps',
                                  'coordinates': 'Native read position after native orientation/soft-clip '
                                                 'handling, not genomic coordinate. Preserve x unchanged and the '
                                                 'soft-clip defect qualification.',
                                  'uncertainty': 'not reported',
                                  'missing_behavior': 'Absent MD yields no known mismatch information; zero '
                                                      'displayed mismatch is not proof of error-free alignment.',
                                  'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                  'source_field_ids': ['legacy_alignment_errors'],
                                  'native_precision_description': 'exact unclustered integer token; clustered '
                                                                  'variants must use '
                                                                  'native_normalized/native_rounded metric suffix '
                                                                  '_rounded_bin_mean',
                                  'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                      'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                      'samstat_2_2_3/src/report/stat_report.c',
                                                      'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                      'samstat_2_2_3/src/plot/plot.c',
                                                      'samstat_2_2_3/src/plot/plot_interval.c',
                                                      'samstat_2_2_3/src/plot/plot_group.c'],
                                  'qualifications': ['Pinned parse_alignment advances sequence cursor by one for '
                                                     'any S operation, not its length; native reconstructed '
                                                     'mismatch assignment after multi-base soft clipping can be '
                                                     'wrong. Preserve native output; no silent correction.']},
 'samstat_legacy_mean_phred': {'metric': 'samstat_legacy_mean_phred',
                               'formats': ['samstat_html_2_2_3'],
                               'section_key': 'samstat_quality_start',
                               'native_fields': ['2.2.3 SAM/BAM bq_R{mate}_{bin}_{offset}.y; bq_R*_end_*.y; '
                                                 'bq_norm_R*.y'],
                               'units': ['phred'],
                               'axis_kinds': ['base_closed_1',
                                              'base_offset_from_end_0',
                                              'read_fraction_bin_0_100',
                                              'native_label'],
                               'population_keys': ['samstat_report_records',
                                                   'samstat_mapq_ge30',
                                                   'samstat_mapq_10_29',
                                                   'samstat_mapq_0_9',
                                                   'samstat_unmapped',
                                                   'samstat_report_sequences'],
                               'meaning': 'native_normalized',
                               'precision': 'native_rounded',
                               'value_domain': 'nonnegative_number',
                               'interpretation': 'SAM/BAM quality-bearing bases of the named stratum/position; '
                                                 'missing qualities omitted; for clustered axes statistics use '
                                                 'rounded cluster histograms',
                               'denominator': 'n quality-bearing bases at that position is not emitted; '
                                              'mean=sum(cq*q)/n; SEM=sqrt(sum(cq*(q-mean)^2)/n)/sqrt(n)',
                               'coordinates': 'Same position conventions as corresponding base plot; native '
                                              'series number is a group offset, not a quality score',
                               'uncertainty': 'error_y.array is native SEM under population-variance formula, not '
                                              'SD, confidence, or posterior probability',
                               'missing_behavior': 'Default collector: all qualities missing -> no quality '
                                                   'series. At an individual emitted position, zero mean can be '
                                                   'Q0 or empty-histogram placeholder because n is not retained; '
                                                   'preserve zero and samstat_quality_coverage_unproven where '
                                                   'ambiguous, not a fabricated missing-value decision. Optional '
                                                   'end/relative collectors lack the default missing-QUAL guard; '
                                                   'record that source-established limitation without claiming '
                                                   'unrun behavior.',
                               'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                               'source_field_ids': ['legacy_quality_mean_sem'],
                               'native_precision_description': 'native_rounded: %.6f; score indices capped at 41 '
                                                               'before summary',
                               'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                   'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                   'samstat_2_2_3/src/report/stat_report.c',
                                                   'samstat_2_2_3/src/plot/plot.c',
                                                   'samstat_2_2_3/src/plot/plot_interval.c',
                                                   'samstat_2_2_3/src/plot/plot_group.c'],
                               'qualifications': ['Do not send these means to quality_phred_v1, which requires a '
                                                  'histogram and actual quality population.',
                                                  'Do not combine position SEMs into a whole-file uncertainty '
                                                  'without covariance/sample sizes.',
                                                  'samstat_quality_coverage_unproven is a '
                                                  'missing-denominator/producer-coverage qualification, not a '
                                                  'confidence penalty. Missing-quality optional SAM/BAM runs were '
                                                  'not executed.']},
 'samstat_legacy_phred_sem': {'metric': 'samstat_legacy_phred_sem',
                              'formats': ['samstat_html_2_2_3'],
                              'section_key': 'samstat_quality_start',
                              'native_fields': ['2.2.3 SAM/BAM corresponding bq*.error_y.array'],
                              'units': ['phred_deviation'],
                              'axis_kinds': ['base_closed_1',
                                             'base_offset_from_end_0',
                                             'read_fraction_bin_0_100',
                                             'native_label'],
                              'population_keys': ['samstat_report_records',
                                                  'samstat_mapq_ge30',
                                                  'samstat_mapq_10_29',
                                                  'samstat_mapq_0_9',
                                                  'samstat_unmapped',
                                                  'samstat_report_sequences'],
                              'meaning': 'native_normalized',
                              'precision': 'native_rounded',
                              'value_domain': 'nonnegative_number',
                              'interpretation': 'SAM/BAM quality-bearing bases of the named stratum/position; '
                                                'missing qualities omitted; for clustered axes statistics use '
                                                'rounded cluster histograms',
                              'denominator': 'n quality-bearing bases at that position is not emitted; '
                                             'mean=sum(cq*q)/n; SEM=sqrt(sum(cq*(q-mean)^2)/n)/sqrt(n)',
                              'coordinates': 'Same position conventions as corresponding base plot; native series '
                                             'number is a group offset, not a quality score',
                              'uncertainty': 'error_y.array is native SEM under population-variance formula, not '
                                             'SD, confidence, or posterior probability',
                              'missing_behavior': 'Default collector: all qualities missing -> no quality series. '
                                                  'At an individual emitted position, zero mean can be Q0 or '
                                                  'empty-histogram placeholder because n is not retained; '
                                                  'preserve zero and samstat_quality_coverage_unproven where '
                                                  'ambiguous, not a fabricated missing-value decision. Optional '
                                                  'end/relative collectors lack the default missing-QUAL guard; '
                                                  'record that source-established limitation without claiming '
                                                  'unrun behavior.',
                              'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                              'source_field_ids': ['legacy_quality_mean_sem'],
                              'native_precision_description': 'native_rounded: %.6f; score indices capped at 41 '
                                                              'before summary',
                              'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                  'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                  'samstat_2_2_3/src/report/stat_report.c',
                                                  'samstat_2_2_3/src/plot/plot.c',
                                                  'samstat_2_2_3/src/plot/plot_interval.c',
                                                  'samstat_2_2_3/src/plot/plot_group.c'],
                              'qualifications': ['Do not send these means to quality_phred_v1, which requires a '
                                                 'histogram and actual quality population.',
                                                 'Do not combine position SEMs into a whole-file uncertainty '
                                                 'without covariance/sample sizes.',
                                                 'samstat_quality_coverage_unproven is a '
                                                 'missing-denominator/producer-coverage qualification, not a '
                                                 'confidence penalty. Missing-quality optional SAM/BAM runs were '
                                                 'not executed.']},
 'samstat_legacy_quality_index_mean': {'metric': 'samstat_legacy_quality_index_mean',
                                       'formats': ['samstat_html_2_2_3'],
                                       'section_key': 'samstat_quality_start',
                                       'native_fields': ['2.2.3 FASTX bq*.y with native offset-zero/capped-index '
                                                         'defect'],
                                       'units': ['dimensionless'],
                                       'axis_kinds': ['base_closed_1',
                                                      'base_offset_from_end_0',
                                                      'read_fraction_bin_0_100',
                                                      'native_label'],
                                       'population_keys': ['samstat_report_records',
                                                           'samstat_mapq_ge30',
                                                           'samstat_mapq_10_29',
                                                           'samstat_mapq_0_9',
                                                           'samstat_unmapped',
                                                           'samstat_report_sequences'],
                                       'meaning': 'native_normalized',
                                       'precision': 'native_rounded',
                                       'value_domain': 'nonnegative_number',
                                       'interpretation': 'FASTX character indices left at offset 0 in pinned '
                                                         '2.2.3 build, capped at 41; these are not decoded '
                                                         'biological Phred values',
                                       'denominator': 'Native arithmetic summary as above, but over incorrectly '
                                                      'decoded/capped indices',
                                       'coordinates': 'same as legacy quality axes',
                                       'uncertainty': 'Native SEM of native indices only; not valid Phred SEM',
                                       'missing_behavior': 'Keep actual numbers and '
                                                           'samstat_fastx_quality_offset_defect diagnostic; do '
                                                           'not repair with an assumed offset or recompute from '
                                                           'unretained input.',
                                       'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                          'PARSER_CALCULATOR_PORTS_002.md',
                                       'source_field_ids': ['legacy_fastx_quality_index_defect'],
                                       'native_precision_description': 'native_rounded %.6f with known producer '
                                                                       'limitation',
                                       'source_evidence': ['samstat_2_2_3/src/tld/src/seq/tld-seqio.c',
                                                           'samstat_2_2_3/src/tld/src/seq/tld-seqbuffer.c',
                                                           'samstat_2_2_3/src/collect/collect.c',
                                                           'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                           'samstat_2_2_3/src/report/stat_report.c',
                                                           'samstat_2_2_3/src/plot/plot.c',
                                                           'samstat_2_2_3/src/plot/plot_interval.c',
                                                           'samstat_2_2_3/src/plot/plot_group.c'],
                                       'qualifications': ['Observed on this pinned source execution. Does not '
                                                          'establish a defect in an unknown BV-BRC deployed '
                                                          'executable.']},
 'samstat_legacy_quality_index_sem': {'metric': 'samstat_legacy_quality_index_sem',
                                      'formats': ['samstat_html_2_2_3'],
                                      'section_key': 'samstat_quality_start',
                                      'native_fields': ['2.2.3 FASTX bq*.error_y.array with native '
                                                        'offset-zero/capped-index defect'],
                                      'units': ['dimensionless'],
                                      'axis_kinds': ['base_closed_1',
                                                     'base_offset_from_end_0',
                                                     'read_fraction_bin_0_100',
                                                     'native_label'],
                                      'population_keys': ['samstat_report_records',
                                                          'samstat_mapq_ge30',
                                                          'samstat_mapq_10_29',
                                                          'samstat_mapq_0_9',
                                                          'samstat_unmapped',
                                                          'samstat_report_sequences'],
                                      'meaning': 'native_normalized',
                                      'precision': 'native_rounded',
                                      'value_domain': 'nonnegative_number',
                                      'interpretation': 'FASTX character indices left at offset 0 in pinned 2.2.3 '
                                                        'build, capped at 41; these are not decoded biological '
                                                        'Phred values',
                                      'denominator': 'Native arithmetic summary as above, but over incorrectly '
                                                     'decoded/capped indices',
                                      'coordinates': 'same as legacy quality axes',
                                      'uncertainty': 'Native SEM of native indices only; not valid Phred SEM',
                                      'missing_behavior': 'Keep actual numbers and '
                                                          'samstat_fastx_quality_offset_defect diagnostic; do not '
                                                          'repair with an assumed offset or recompute from '
                                                          'unretained input.',
                                      'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                         'PARSER_CALCULATOR_PORTS_002.md',
                                      'source_field_ids': ['legacy_fastx_quality_index_defect'],
                                      'native_precision_description': 'native_rounded %.6f with known producer '
                                                                      'limitation',
                                      'source_evidence': ['samstat_2_2_3/src/tld/src/seq/tld-seqio.c',
                                                          'samstat_2_2_3/src/tld/src/seq/tld-seqbuffer.c',
                                                          'samstat_2_2_3/src/collect/collect.c',
                                                          'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                          'samstat_2_2_3/src/report/stat_report.c',
                                                          'samstat_2_2_3/src/plot/plot.c',
                                                          'samstat_2_2_3/src/plot/plot_interval.c',
                                                          'samstat_2_2_3/src/plot/plot_group.c'],
                                      'qualifications': ['Observed on this pinned source execution. Does not '
                                                         'establish a defect in an unknown BV-BRC deployed '
                                                         'executable.']},
 'samstat_length_density': {'metric': 'samstat_length_density',
                            'formats': ['samstat_html_2_2_3'],
                            'section_key': 'samstat_length',
                            'native_fields': ['len_R1__{bin}.x / .y', 'len_R2__{bin}.x / .y'],
                            'units': ['inverse_bp'],
                            'axis_kinds': ['length_closed'],
                            'population_keys': ['samstat_report_records',
                                                'samstat_mapq_ge30',
                                                'samstat_mapq_10_29',
                                                'samstat_mapq_0_9',
                                                'samstat_unmapped',
                                                'samstat_report_sequences'],
                            'meaning': 'native_estimate',
                            'precision': 'native_estimator',
                            'value_domain': 'nonnegative_number',
                            'interpretation': 'SAM/BAM soft-clip-trimmed sequence lengths (length-clip5-clip3), '
                                              'by mate/MAPQ stratum; FASTA/FASTQ full lengths. Missing sequence '
                                              'may contribute length zero; no positive sequence length is '
                                              'fabricated.',
                            'denominator': 'Weighted normal KDE divided by total weighted observations, not '
                                           'native read counts; bandwidth population SD*(3N/4)^(-1/5)',
                            'coordinates': 'x is an observed length in bp; points are not exhaustive integer '
                                           'histogram bins',
                            'uncertainty': 'No interval or estimator variance emitted',
                            'missing_behavior': 'Missing series stays absent. Single unique length is native '
                                                'fallback y=1.000000, diagnosed native_fallback_value. Do not '
                                                'invert density into counts.',
                            'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                            'source_field_ids': ['legacy_length_density'],
                            'native_precision_description': 'native_estimator; x and y formatted %.6f',
                            'source_evidence': ['samstat_2_2_3/src/plot/plot.c',
                                                'samstat_2_2_3/src/plot/plot_interval.c',
                                                'samstat_2_2_3/src/plot/plot_group.c',
                                                'samstat_2_2_3/src/tld/src/stats/kde.c'],
                            'qualifications': ['The native y-axis label Counts does not change its density '
                                               'meaning.']},
 'samstat_mapped_note_record_count': {'metric': 'samstat_mapped_note_record_count',
                                      'formats': ['samstat_html_2_5_0'],
                                      'section_key': 'samstat_notes',
                                      'native_fields': ['2.5.0 either unavailable note X of Y mapped reads: Y; '
                                                        'repeated denominator retained'],
                                      'units': ['alignment_records'],
                                      'axis_kinds': ['none'],
                                      'population_keys': ['samstat_report_records',
                                                          'samstat_mapq_ge30',
                                                          'samstat_mapq_10_29',
                                                          'samstat_mapq_0_9',
                                                          'samstat_unmapped',
                                                          'samstat_report_sequences'],
                                      'meaning': 'observed_count',
                                      'precision': 'exact_for_retained_population',
                                      'value_domain': 'nonnegative_integer',
                                      'interpretation': 'Numerator is the named unavailable/excluded population. '
                                                        'Note denominator is mapped primary report records. '
                                                        'Display threshold 50 is producer configuration, not a '
                                                        'measurement. Excluded secondary/supplementary records '
                                                        'are not contributors.',
                                      'denominator': 'Named note denominator only, not all primary records for '
                                                     'missing-data fractions',
                                      'coordinates': 'none',
                                      'uncertainty': 'not reported',
                                      'missing_behavior': 'Conditional note absence is not parsed as observed '
                                                          'zero; preserve unsupported/absent section if not '
                                                          'recognizable.',
                                      'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                         'PARSER_CALCULATOR_PORTS_002.md',
                                      'source_field_ids': ['modern_data_coverage_notes'],
                                      'native_precision_description': 'exact comma-separated integer tokens',
                                      'source_evidence': ['samstat/src/collect/collect.c',
                                                          'samstat/src/htsinterface/htsglue.c',
                                                          'samstat/src/report/stat_report.c',
                                                          'samstat/src/report/report_help.c'],
                                      'qualifications': []},
 'samstat_max_length': {'metric': 'samstat_max_length',
                        'formats': ['samstat_html_2_5_0'],
                        'section_key': 'samstat_length',
                        'native_fields': ['2.5.0 plot1 accessible desc Read lengths range from MIN to MAX: MAX '
                                          'token; global even in mate figures'],
                        'units': ['bp', 'kbp', 'Mbp'],
                        'axis_kinds': ['none'],
                        'population_keys': ['samstat_report_records',
                                            'samstat_mapq_ge30',
                                            'samstat_mapq_10_29',
                                            'samstat_mapq_0_9',
                                            'samstat_unmapped',
                                            'samstat_report_sequences'],
                        'meaning': 'observed_native',
                        'precision': 'exact_for_retained_population',
                        'value_domain': 'nonnegative_number',
                        'interpretation': 'Full sequence lengths of primary records/FASTX sequences; absent SEQ '
                                          'contributes no positive length',
                        'denominator': 'Median lower quantile of length counts; N50 length threshold for half of '
                                       'total bases, native length-bin representation',
                        'coordinates': 'Length units, not reference coordinates; min/max descriptions repeat '
                                       'global extrema in each mate figure',
                        'uncertainty': 'No uncertainty interval; binning/format precision only',
                        'missing_behavior': 'No sequence -> n/a; no histogram distribution recoverable from SVG '
                                            'paths.',
                        'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                        'allowed_precisions': ['exact_for_retained_population',
                                               'native_rounded',
                                               'native_estimator',
                                               'not_reported'],
                        'source_field_ids': ['modern_lengths'],
                        'native_precision_description': 'Native integer bp below display cutoff; large values '
                                                        'rounded to one decimal kb/Mb. Tilde marks lower-edge '
                                                        'storage-bin estimate, keep native_estimator and original '
                                                        'token. Never claim exact bp from rounded unit display.',
                        'source_evidence': ['samstat/src/collect/collect.c',
                                            'samstat/src/htsinterface/htsglue.c',
                                            'samstat/src/report/stat_report.c',
                                            'samstat/src/plot/report_plots.c',
                                            'samstat/src/plot/report_fmt.h'],
                        'qualifications': ['Native storage bins are exact below 1000 and approximately 1% '
                                           'logarithmic above; display units create additional rounding. '
                                           'Uniform-length reports can refine native median/N50.']},
 'samstat_max_read_quality_bin': {'metric': 'samstat_max_read_quality_bin',
                                  'formats': ['samstat_html_2_5_0'],
                                  'section_key': 'samstat_quality_start',
                                  'native_fields': ['2.5.0 plot2 desc mean base quality from QMIN to QMAX: MAX '
                                                    'integer bin'],
                                  'units': ['phred'],
                                  'axis_kinds': ['quality_score'],
                                  'population_keys': ['samstat_report_records',
                                                      'samstat_mapq_ge30',
                                                      'samstat_mapq_10_29',
                                                      'samstat_mapq_0_9',
                                                      'samstat_unmapped',
                                                      'samstat_report_sequences'],
                                  'meaning': 'observed_native',
                                  'precision': 'exact_for_retained_population',
                                  'value_domain': 'nonnegative_integer',
                                  'interpretation': 'Across all mates and mapping strata with quality-bearing '
                                                    'reads; the same global extrema repeat in both mate figures',
                                  'denominator': 'Per-read error-probability mean assigned to native integer '
                                                 'quality bin',
                                  'coordinates': 'Quality-bin index, axis quality_score',
                                  'uncertainty': 'not reported',
                                  'missing_behavior': 'No quality -> no range. SVG x ticks are plotting '
                                                      'configuration and must not be promoted to data.',
                                  'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                  'source_field_ids': ['modern_quality_range'],
                                  'native_precision_description': 'integer bin indices, not exact unbinned '
                                                                  'quality extrema',
                                  'source_evidence': ['samstat/src/plot/report_plots.c',
                                                      'samstat/src/collect/collect.c'],
                                  'qualifications': []},
 'samstat_median_length': {'metric': 'samstat_median_length',
                           'formats': ['samstat_html_2_5_0'],
                           'section_key': 'samstat_length',
                           'native_fields': ['2.5.0 header reads(median LENGTH) native value and unit'],
                           'units': ['bp', 'kbp', 'Mbp'],
                           'axis_kinds': ['none'],
                           'population_keys': ['samstat_report_records',
                                               'samstat_mapq_ge30',
                                               'samstat_mapq_10_29',
                                               'samstat_mapq_0_9',
                                               'samstat_unmapped',
                                               'samstat_report_sequences'],
                           'meaning': 'native_estimate',
                           'precision': 'exact_for_retained_population',
                           'value_domain': 'nonnegative_number',
                           'interpretation': 'Full sequence lengths of primary records/FASTX sequences; absent '
                                             'SEQ contributes no positive length',
                           'denominator': 'Median lower quantile of length counts; N50 length threshold for half '
                                          'of total bases, native length-bin representation',
                           'coordinates': 'Length units, not reference coordinates; min/max descriptions repeat '
                                          'global extrema in each mate figure',
                           'uncertainty': 'No uncertainty interval; binning/format precision only',
                           'missing_behavior': 'No sequence -> n/a; no histogram distribution recoverable from '
                                               'SVG paths.',
                           'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                           'allowed_precisions': ['exact_for_retained_population',
                                                  'native_rounded',
                                                  'native_estimator',
                                                  'not_reported'],
                           'source_field_ids': ['modern_lengths'],
                           'native_precision_description': 'Native integer bp below display cutoff; large values '
                                                           'rounded to one decimal kb/Mb. Tilde marks lower-edge '
                                                           'storage-bin estimate, keep native_estimator and '
                                                           'original token. Never claim exact bp from rounded '
                                                           'unit display.',
                           'source_evidence': ['samstat/src/collect/collect.c',
                                               'samstat/src/htsinterface/htsglue.c',
                                               'samstat/src/report/stat_report.c',
                                               'samstat/src/plot/report_plots.c',
                                               'samstat/src/plot/report_fmt.h'],
                           'qualifications': ['Native storage bins are exact below 1000 and approximately 1% '
                                              'logarithmic above; display units create additional rounding. '
                                              'Uniform-length reports can refine native median/N50.']},
 'samstat_min_length': {'metric': 'samstat_min_length',
                        'formats': ['samstat_html_2_5_0'],
                        'section_key': 'samstat_length',
                        'native_fields': ['2.5.0 plot1 accessible desc Read lengths range from MIN to MAX: MIN '
                                          'token; global even in mate figures'],
                        'units': ['bp', 'kbp', 'Mbp'],
                        'axis_kinds': ['none'],
                        'population_keys': ['samstat_report_records',
                                            'samstat_mapq_ge30',
                                            'samstat_mapq_10_29',
                                            'samstat_mapq_0_9',
                                            'samstat_unmapped',
                                            'samstat_report_sequences'],
                        'meaning': 'observed_native',
                        'precision': 'exact_for_retained_population',
                        'value_domain': 'nonnegative_number',
                        'interpretation': 'Full sequence lengths of primary records/FASTX sequences; absent SEQ '
                                          'contributes no positive length',
                        'denominator': 'Median lower quantile of length counts; N50 length threshold for half of '
                                       'total bases, native length-bin representation',
                        'coordinates': 'Length units, not reference coordinates; min/max descriptions repeat '
                                       'global extrema in each mate figure',
                        'uncertainty': 'No uncertainty interval; binning/format precision only',
                        'missing_behavior': 'No sequence -> n/a; no histogram distribution recoverable from SVG '
                                            'paths.',
                        'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                        'allowed_precisions': ['exact_for_retained_population',
                                               'native_rounded',
                                               'native_estimator',
                                               'not_reported'],
                        'source_field_ids': ['modern_lengths'],
                        'native_precision_description': 'Native integer bp below display cutoff; large values '
                                                        'rounded to one decimal kb/Mb. Tilde marks lower-edge '
                                                        'storage-bin estimate, keep native_estimator and original '
                                                        'token. Never claim exact bp from rounded unit display.',
                        'source_evidence': ['samstat/src/collect/collect.c',
                                            'samstat/src/htsinterface/htsglue.c',
                                            'samstat/src/report/stat_report.c',
                                            'samstat/src/plot/report_plots.c',
                                            'samstat/src/plot/report_fmt.h'],
                        'qualifications': ['Native storage bins are exact below 1000 and approximately 1% '
                                           'logarithmic above; display units create additional rounding. '
                                           'Uniform-length reports can refine native median/N50.']},
 'samstat_min_read_quality_bin': {'metric': 'samstat_min_read_quality_bin',
                                  'formats': ['samstat_html_2_5_0'],
                                  'section_key': 'samstat_quality_start',
                                  'native_fields': ['2.5.0 plot2 desc mean base quality from QMIN to QMAX: MIN '
                                                    'integer bin'],
                                  'units': ['phred'],
                                  'axis_kinds': ['quality_score'],
                                  'population_keys': ['samstat_report_records',
                                                      'samstat_mapq_ge30',
                                                      'samstat_mapq_10_29',
                                                      'samstat_mapq_0_9',
                                                      'samstat_unmapped',
                                                      'samstat_report_sequences'],
                                  'meaning': 'observed_native',
                                  'precision': 'exact_for_retained_population',
                                  'value_domain': 'nonnegative_integer',
                                  'interpretation': 'Across all mates and mapping strata with quality-bearing '
                                                    'reads; the same global extrema repeat in both mate figures',
                                  'denominator': 'Per-read error-probability mean assigned to native integer '
                                                 'quality bin',
                                  'coordinates': 'Quality-bin index, axis quality_score',
                                  'uncertainty': 'not reported',
                                  'missing_behavior': 'No quality -> no range. SVG x ticks are plotting '
                                                      'configuration and must not be promoted to data.',
                                  'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                  'source_field_ids': ['modern_quality_range'],
                                  'native_precision_description': 'integer bin indices, not exact unbinned '
                                                                  'quality extrema',
                                  'source_evidence': ['samstat/src/plot/report_plots.c',
                                                      'samstat/src/collect/collect.c'],
                                  'qualifications': []},
 'samstat_mismatch_A_count': {'metric': 'samstat_mismatch_A_count',
                              'formats': ['samstat_html_2_2_3'],
                              'section_key': 'samstat_mismatch',
                              'native_fields': ['2.2.3 mis_R{mate}_{bin}_A.y; read-base symbolA; unclustered '
                                                'integer'],
                              'units': ['bases'],
                              'axis_kinds': ['base_closed_1',
                                             'base_offset_from_end_0',
                                             'read_fraction_bin_0_100',
                                             'native_label'],
                              'population_keys': ['samstat_report_records',
                                                  'samstat_mapq_ge30',
                                                  'samstat_mapq_10_29',
                                                  'samstat_mapq_0_9',
                                                  'samstat_unmapped',
                                                  'samstat_report_sequences'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Error events reconstructed by native CIGAR/MD processing for '
                                                'named mate/MAPQ stratum; mismatch base labels describe read '
                                                'bases',
                              'denominator': 'No coverage denominator or native error rate emitted; indel values '
                                             'count gap openings, not bases in gaps',
                              'coordinates': 'Native read position after native orientation/soft-clip handling, '
                                             'not genomic coordinate. Preserve x unchanged and the soft-clip '
                                             'defect qualification.',
                              'uncertainty': 'not reported',
                              'missing_behavior': 'Absent MD yields no known mismatch information; zero displayed '
                                                  'mismatch is not proof of error-free alignment.',
                              'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                              'source_field_ids': ['legacy_alignment_errors'],
                              'native_precision_description': 'exact unclustered integer token; clustered '
                                                              'variants must use native_normalized/native_rounded '
                                                              'metric suffix _rounded_bin_mean',
                              'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                  'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                  'samstat_2_2_3/src/report/stat_report.c',
                                                  'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                  'samstat_2_2_3/src/plot/plot.c',
                                                  'samstat_2_2_3/src/plot/plot_interval.c',
                                                  'samstat_2_2_3/src/plot/plot_group.c'],
                              'qualifications': ['Pinned parse_alignment advances sequence cursor by one for any '
                                                 'S operation, not its length; native reconstructed mismatch '
                                                 'assignment after multi-base soft clipping can be wrong. '
                                                 'Preserve native output; no silent correction.']},
 'samstat_mismatch_C_count': {'metric': 'samstat_mismatch_C_count',
                              'formats': ['samstat_html_2_2_3'],
                              'section_key': 'samstat_mismatch',
                              'native_fields': ['2.2.3 mis_R{mate}_{bin}_C.y; read-base symbolC; unclustered '
                                                'integer'],
                              'units': ['bases'],
                              'axis_kinds': ['base_closed_1',
                                             'base_offset_from_end_0',
                                             'read_fraction_bin_0_100',
                                             'native_label'],
                              'population_keys': ['samstat_report_records',
                                                  'samstat_mapq_ge30',
                                                  'samstat_mapq_10_29',
                                                  'samstat_mapq_0_9',
                                                  'samstat_unmapped',
                                                  'samstat_report_sequences'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Error events reconstructed by native CIGAR/MD processing for '
                                                'named mate/MAPQ stratum; mismatch base labels describe read '
                                                'bases',
                              'denominator': 'No coverage denominator or native error rate emitted; indel values '
                                             'count gap openings, not bases in gaps',
                              'coordinates': 'Native read position after native orientation/soft-clip handling, '
                                             'not genomic coordinate. Preserve x unchanged and the soft-clip '
                                             'defect qualification.',
                              'uncertainty': 'not reported',
                              'missing_behavior': 'Absent MD yields no known mismatch information; zero displayed '
                                                  'mismatch is not proof of error-free alignment.',
                              'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                              'source_field_ids': ['legacy_alignment_errors'],
                              'native_precision_description': 'exact unclustered integer token; clustered '
                                                              'variants must use native_normalized/native_rounded '
                                                              'metric suffix _rounded_bin_mean',
                              'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                  'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                  'samstat_2_2_3/src/report/stat_report.c',
                                                  'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                  'samstat_2_2_3/src/plot/plot.c',
                                                  'samstat_2_2_3/src/plot/plot_interval.c',
                                                  'samstat_2_2_3/src/plot/plot_group.c'],
                              'qualifications': ['Pinned parse_alignment advances sequence cursor by one for any '
                                                 'S operation, not its length; native reconstructed mismatch '
                                                 'assignment after multi-base soft clipping can be wrong. '
                                                 'Preserve native output; no silent correction.']},
 'samstat_mismatch_G_count': {'metric': 'samstat_mismatch_G_count',
                              'formats': ['samstat_html_2_2_3'],
                              'section_key': 'samstat_mismatch',
                              'native_fields': ['2.2.3 mis_R{mate}_{bin}_G.y; read-base symbolG; unclustered '
                                                'integer'],
                              'units': ['bases'],
                              'axis_kinds': ['base_closed_1',
                                             'base_offset_from_end_0',
                                             'read_fraction_bin_0_100',
                                             'native_label'],
                              'population_keys': ['samstat_report_records',
                                                  'samstat_mapq_ge30',
                                                  'samstat_mapq_10_29',
                                                  'samstat_mapq_0_9',
                                                  'samstat_unmapped',
                                                  'samstat_report_sequences'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Error events reconstructed by native CIGAR/MD processing for '
                                                'named mate/MAPQ stratum; mismatch base labels describe read '
                                                'bases',
                              'denominator': 'No coverage denominator or native error rate emitted; indel values '
                                             'count gap openings, not bases in gaps',
                              'coordinates': 'Native read position after native orientation/soft-clip handling, '
                                             'not genomic coordinate. Preserve x unchanged and the soft-clip '
                                             'defect qualification.',
                              'uncertainty': 'not reported',
                              'missing_behavior': 'Absent MD yields no known mismatch information; zero displayed '
                                                  'mismatch is not proof of error-free alignment.',
                              'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                              'source_field_ids': ['legacy_alignment_errors'],
                              'native_precision_description': 'exact unclustered integer token; clustered '
                                                              'variants must use native_normalized/native_rounded '
                                                              'metric suffix _rounded_bin_mean',
                              'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                  'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                  'samstat_2_2_3/src/report/stat_report.c',
                                                  'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                  'samstat_2_2_3/src/plot/plot.c',
                                                  'samstat_2_2_3/src/plot/plot_interval.c',
                                                  'samstat_2_2_3/src/plot/plot_group.c'],
                              'qualifications': ['Pinned parse_alignment advances sequence cursor by one for any '
                                                 'S operation, not its length; native reconstructed mismatch '
                                                 'assignment after multi-base soft clipping can be wrong. '
                                                 'Preserve native output; no silent correction.']},
 'samstat_mismatch_N_count': {'metric': 'samstat_mismatch_N_count',
                              'formats': ['samstat_html_2_2_3'],
                              'section_key': 'samstat_mismatch',
                              'native_fields': ['2.2.3 mis_R{mate}_{bin}_N.y; read-base symbolN; unclustered '
                                                'integer'],
                              'units': ['bases'],
                              'axis_kinds': ['base_closed_1',
                                             'base_offset_from_end_0',
                                             'read_fraction_bin_0_100',
                                             'native_label'],
                              'population_keys': ['samstat_report_records',
                                                  'samstat_mapq_ge30',
                                                  'samstat_mapq_10_29',
                                                  'samstat_mapq_0_9',
                                                  'samstat_unmapped',
                                                  'samstat_report_sequences'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Error events reconstructed by native CIGAR/MD processing for '
                                                'named mate/MAPQ stratum; mismatch base labels describe read '
                                                'bases',
                              'denominator': 'No coverage denominator or native error rate emitted; indel values '
                                             'count gap openings, not bases in gaps',
                              'coordinates': 'Native read position after native orientation/soft-clip handling, '
                                             'not genomic coordinate. Preserve x unchanged and the soft-clip '
                                             'defect qualification.',
                              'uncertainty': 'not reported',
                              'missing_behavior': 'Absent MD yields no known mismatch information; zero displayed '
                                                  'mismatch is not proof of error-free alignment.',
                              'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                              'source_field_ids': ['legacy_alignment_errors'],
                              'native_precision_description': 'exact unclustered integer token; clustered '
                                                              'variants must use native_normalized/native_rounded '
                                                              'metric suffix _rounded_bin_mean',
                              'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                  'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                  'samstat_2_2_3/src/report/stat_report.c',
                                                  'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                  'samstat_2_2_3/src/plot/plot.c',
                                                  'samstat_2_2_3/src/plot/plot_interval.c',
                                                  'samstat_2_2_3/src/plot/plot_group.c'],
                              'qualifications': ['Pinned parse_alignment advances sequence cursor by one for any '
                                                 'S operation, not its length; native reconstructed mismatch '
                                                 'assignment after multi-base soft clipping can be wrong. '
                                                 'Preserve native output; no silent correction.']},
 'samstat_mismatch_T_count': {'metric': 'samstat_mismatch_T_count',
                              'formats': ['samstat_html_2_2_3'],
                              'section_key': 'samstat_mismatch',
                              'native_fields': ['2.2.3 mis_R{mate}_{bin}_T.y; read-base symbolT; unclustered '
                                                'integer'],
                              'units': ['bases'],
                              'axis_kinds': ['base_closed_1',
                                             'base_offset_from_end_0',
                                             'read_fraction_bin_0_100',
                                             'native_label'],
                              'population_keys': ['samstat_report_records',
                                                  'samstat_mapq_ge30',
                                                  'samstat_mapq_10_29',
                                                  'samstat_mapq_0_9',
                                                  'samstat_unmapped',
                                                  'samstat_report_sequences'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Error events reconstructed by native CIGAR/MD processing for '
                                                'named mate/MAPQ stratum; mismatch base labels describe read '
                                                'bases',
                              'denominator': 'No coverage denominator or native error rate emitted; indel values '
                                             'count gap openings, not bases in gaps',
                              'coordinates': 'Native read position after native orientation/soft-clip handling, '
                                             'not genomic coordinate. Preserve x unchanged and the soft-clip '
                                             'defect qualification.',
                              'uncertainty': 'not reported',
                              'missing_behavior': 'Absent MD yields no known mismatch information; zero displayed '
                                                  'mismatch is not proof of error-free alignment.',
                              'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                              'source_field_ids': ['legacy_alignment_errors'],
                              'native_precision_description': 'exact unclustered integer token; clustered '
                                                              'variants must use native_normalized/native_rounded '
                                                              'metric suffix _rounded_bin_mean',
                              'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                  'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                  'samstat_2_2_3/src/report/stat_report.c',
                                                  'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                  'samstat_2_2_3/src/plot/plot.c',
                                                  'samstat_2_2_3/src/plot/plot_interval.c',
                                                  'samstat_2_2_3/src/plot/plot_group.c'],
                              'qualifications': ['Pinned parse_alignment advances sequence cursor by one for any '
                                                 'S operation, not its length; native reconstructed mismatch '
                                                 'assignment after multi-base soft clipping can be wrong. '
                                                 'Preserve native output; no silent correction.']},
 'samstat_mismatch_unavailable_record_count': {'metric': 'samstat_mismatch_unavailable_record_count',
                                               'formats': ['samstat_html_2_5_0'],
                                               'section_key': 'samstat_notes',
                                               'native_fields': ['2.5.0 notes Mismatch profile excludes X of Y '
                                                                 'mapped reads: X'],
                                               'units': ['alignment_records'],
                                               'axis_kinds': ['none'],
                                               'population_keys': ['samstat_report_records',
                                                                   'samstat_mapq_ge30',
                                                                   'samstat_mapq_10_29',
                                                                   'samstat_mapq_0_9',
                                                                   'samstat_unmapped',
                                                                   'samstat_report_sequences'],
                                               'meaning': 'observed_count',
                                               'precision': 'exact_for_retained_population',
                                               'value_domain': 'nonnegative_integer',
                                               'interpretation': 'Numerator is the named unavailable/excluded '
                                                                 'population. Note denominator is mapped primary '
                                                                 'report records. Display threshold 50 is '
                                                                 'producer configuration, not a measurement. '
                                                                 'Excluded secondary/supplementary records are '
                                                                 'not contributors.',
                                               'denominator': 'Named note denominator only, not all primary '
                                                              'records for missing-data fractions',
                                               'coordinates': 'none',
                                               'uncertainty': 'not reported',
                                               'missing_behavior': 'Conditional note absence is not parsed as '
                                                                   'observed zero; preserve unsupported/absent '
                                                                   'section if not recognizable.',
                                               'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                                  'PARSER_CALCULATOR_PORTS_002.md',
                                               'source_field_ids': ['modern_data_coverage_notes'],
                                               'native_precision_description': 'exact comma-separated integer '
                                                                               'tokens',
                                               'source_evidence': ['samstat/src/collect/collect.c',
                                                                   'samstat/src/htsinterface/htsglue.c',
                                                                   'samstat/src/report/stat_report.c',
                                                                   'samstat/src/report/report_help.c'],
                                               'qualifications': []},
 'samstat_n50_length': {'metric': 'samstat_n50_length',
                        'formats': ['samstat_html_2_5_0'],
                        'section_key': 'samstat_length',
                        'native_fields': ['2.5.0 strip N50 dd main LENGTH value and unit'],
                        'units': ['bp', 'kbp', 'Mbp'],
                        'axis_kinds': ['none'],
                        'population_keys': ['samstat_report_records',
                                            'samstat_mapq_ge30',
                                            'samstat_mapq_10_29',
                                            'samstat_mapq_0_9',
                                            'samstat_unmapped',
                                            'samstat_report_sequences'],
                        'meaning': 'native_estimate',
                        'precision': 'exact_for_retained_population',
                        'value_domain': 'nonnegative_number',
                        'interpretation': 'Full sequence lengths of primary records/FASTX sequences; absent SEQ '
                                          'contributes no positive length',
                        'denominator': 'Median lower quantile of length counts; N50 length threshold for half of '
                                       'total bases, native length-bin representation',
                        'coordinates': 'Length units, not reference coordinates; min/max descriptions repeat '
                                       'global extrema in each mate figure',
                        'uncertainty': 'No uncertainty interval; binning/format precision only',
                        'missing_behavior': 'No sequence -> n/a; no histogram distribution recoverable from SVG '
                                            'paths.',
                        'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                        'allowed_precisions': ['exact_for_retained_population',
                                               'native_rounded',
                                               'native_estimator',
                                               'not_reported'],
                        'source_field_ids': ['modern_lengths'],
                        'native_precision_description': 'Native integer bp below display cutoff; large values '
                                                        'rounded to one decimal kb/Mb. Tilde marks lower-edge '
                                                        'storage-bin estimate, keep native_estimator and original '
                                                        'token. Never claim exact bp from rounded unit display.',
                        'source_evidence': ['samstat/src/collect/collect.c',
                                            'samstat/src/htsinterface/htsglue.c',
                                            'samstat/src/report/stat_report.c',
                                            'samstat/src/plot/report_plots.c',
                                            'samstat/src/plot/report_fmt.h'],
                        'qualifications': ['Native storage bins are exact below 1000 and approximately 1% '
                                           'logarithmic above; display units create additional rounding. '
                                           'Uniform-length reports can refine native median/N50.']},
 'samstat_paired_flag_percent': {'metric': 'samstat_paired_flag_percent',
                                 'formats': ['samstat_html_2_2_3'],
                                 'section_key': 'samstat_pair_flags',
                                 'native_fields': ['2.2.3 paired in sequencing sentence parenthesized percentage'],
                                 'units': ['percent'],
                                 'axis_kinds': ['none'],
                                 'population_keys': ['samstat_report_records',
                                                     'samstat_mapq_ge30',
                                                     'samstat_mapq_10_29',
                                                     'samstat_mapq_0_9',
                                                     'samstat_unmapped',
                                                     'samstat_report_sequences'],
                                 'meaning': 'native_normalized',
                                 'precision': 'native_rounded',
                                 'value_domain': 'number_0_100',
                                 'interpretation': 'Records with FLAG paired / proper-pair in producer-retained '
                                                   'record set',
                                 'denominator': 'All producer-retained alignment records, including unpaired '
                                                'records. Native one-decimal percentage of paired-flag records; '
                                                'no pair count.',
                                 'coordinates': 'none',
                                 'uncertainty': 'not reported',
                                 'missing_behavior': 'Sentence absent does not establish an observed zero; retain '
                                                     'absence.',
                                 'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                 'source_field_ids': ['legacy_pair_flag_counts'],
                                 'native_precision_description': 'Counts below 1000 exact; >=1000 rounded integer '
                                                                 'K/M/G mantissa, normalized display value in '
                                                                 'alignment_records with native_rounded precision '
                                                                 'and token preserved. Native percentages one '
                                                                 'decimal. Rounded display counts never exact '
                                                                 'cardinality operands.',
                                 'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                     'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                     'samstat_2_2_3/src/report/stat_report.c'],
                                 'qualifications': []},
 'samstat_paired_flag_record_count_display': {'metric': 'samstat_paired_flag_record_count_display',
                                              'formats': ['samstat_html_2_2_3'],
                                              'section_key': 'samstat_pair_flags',
                                              'native_fields': ['2.2.3 paired in sequencing sentence count; '
                                                                'native K/M/G display converted to '
                                                                'alignment-record display units'],
                                              'units': ['alignment_records'],
                                              'axis_kinds': ['none'],
                                              'population_keys': ['samstat_report_records',
                                                                  'samstat_mapq_ge30',
                                                                  'samstat_mapq_10_29',
                                                                  'samstat_mapq_0_9',
                                                                  'samstat_unmapped',
                                                                  'samstat_report_sequences'],
                                              'meaning': 'observed_native',
                                              'precision': 'native_rounded',
                                              'value_domain': 'nonnegative_integer',
                                              'interpretation': 'Records with FLAG paired / proper-pair in '
                                                                'producer-retained record set',
                                              'denominator': None,
                                              'coordinates': 'none',
                                              'uncertainty': 'not reported',
                                              'missing_behavior': 'Sentence absent does not establish an observed '
                                                                  'zero; retain absence.',
                                              'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                                 'PARSER_CALCULATOR_PORTS_002.md',
                                              'allowed_precisions': ['exact_for_retained_population',
                                                                     'native_rounded'],
                                              'source_field_ids': ['legacy_pair_flag_counts'],
                                              'native_precision_description': 'Counts below 1000 exact; >=1000 '
                                                                              'rounded integer K/M/G mantissa, '
                                                                              'normalized display value in '
                                                                              'alignment_records with '
                                                                              'native_rounded precision and token '
                                                                              'preserved. Native percentages one '
                                                                              'decimal. Rounded display counts '
                                                                              'never exact cardinality operands.',
                                              'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                                  'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                                  'samstat_2_2_3/src/report/stat_report.c'],
                                              'qualifications': []},
 'samstat_position_minimum_records': {'metric': 'samstat_position_minimum_records',
                                      'formats': ['samstat_html_2_5_0'],
                                      'section_key': 'samstat_notes',
                                      'native_fields': ['2.5.0 notes/plot-na/accessible desc fewer than N reads '
                                                        'or needs at least N: N configuration'],
                                      'units': ['reads'],
                                      'axis_kinds': ['none'],
                                      'population_keys': ['samstat_report_records',
                                                          'samstat_mapq_ge30',
                                                          'samstat_mapq_10_29',
                                                          'samstat_mapq_0_9',
                                                          'samstat_unmapped',
                                                          'samstat_report_sequences'],
                                      'meaning': 'native_configuration',
                                      'precision': 'exact_for_retained_population',
                                      'value_domain': 'nonnegative_integer',
                                      'interpretation': 'Producer display-coverage threshold in records/reads; '
                                                        'configuration, not an observed population cardinality.',
                                      'denominator': None,
                                      'coordinates': 'none',
                                      'uncertainty': 'not reported',
                                      'missing_behavior': 'Conditional note absence is not parsed as observed '
                                                          'zero; preserve unsupported/absent section if not '
                                                          'recognizable.',
                                      'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                         'PARSER_CALCULATOR_PORTS_002.md',
                                      'source_field_ids': ['modern_data_coverage_notes'],
                                      'native_precision_description': 'exact comma-separated integer tokens',
                                      'source_evidence': ['samstat/src/collect/collect.c',
                                                          'samstat/src/htsinterface/htsglue.c',
                                                          'samstat/src/report/stat_report.c',
                                                          'samstat/src/report/report_help.c'],
                                      'qualifications': []},
 'samstat_proper_pair_flag_percent': {'metric': 'samstat_proper_pair_flag_percent',
                                      'formats': ['samstat_html_2_2_3'],
                                      'section_key': 'samstat_pair_flags',
                                      'native_fields': ['2.2.3 properly paired sentence parenthesized percentage'],
                                      'units': ['percent'],
                                      'axis_kinds': ['none'],
                                      'population_keys': ['samstat_report_records',
                                                          'samstat_mapq_ge30',
                                                          'samstat_mapq_10_29',
                                                          'samstat_mapq_0_9',
                                                          'samstat_unmapped',
                                                          'samstat_report_sequences'],
                                      'meaning': 'native_normalized',
                                      'precision': 'native_rounded',
                                      'value_domain': 'number_0_100',
                                      'interpretation': 'Records with FLAG paired / proper-pair in '
                                                        'producer-retained record set',
                                      'denominator': 'Producer-retained paired-flag alignment records. Native '
                                                     'one-decimal percentage also carrying proper-pair flag; no '
                                                     'pair count.',
                                      'coordinates': 'none',
                                      'uncertainty': 'not reported',
                                      'missing_behavior': 'Sentence absent does not establish an observed zero; '
                                                          'retain absence.',
                                      'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                         'PARSER_CALCULATOR_PORTS_002.md',
                                      'source_field_ids': ['legacy_pair_flag_counts'],
                                      'native_precision_description': 'Counts below 1000 exact; >=1000 rounded '
                                                                      'integer K/M/G mantissa, normalized display '
                                                                      'value in alignment_records with '
                                                                      'native_rounded precision and token '
                                                                      'preserved. Native percentages one decimal. '
                                                                      'Rounded display counts never exact '
                                                                      'cardinality operands.',
                                      'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                          'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                          'samstat_2_2_3/src/report/stat_report.c'],
                                      'qualifications': []},
 'samstat_proper_pair_flag_record_count_display': {'metric': 'samstat_proper_pair_flag_record_count_display',
                                                   'formats': ['samstat_html_2_2_3'],
                                                   'section_key': 'samstat_pair_flags',
                                                   'native_fields': ['2.2.3 properly paired sentence count; '
                                                                     'native K/M/G display converted to '
                                                                     'alignment-record display units'],
                                                   'units': ['alignment_records'],
                                                   'axis_kinds': ['none'],
                                                   'population_keys': ['samstat_report_records',
                                                                       'samstat_mapq_ge30',
                                                                       'samstat_mapq_10_29',
                                                                       'samstat_mapq_0_9',
                                                                       'samstat_unmapped',
                                                                       'samstat_report_sequences'],
                                                   'meaning': 'observed_native',
                                                   'precision': 'native_rounded',
                                                   'value_domain': 'nonnegative_integer',
                                                   'interpretation': 'Records with FLAG paired / proper-pair in '
                                                                     'producer-retained record set',
                                                   'denominator': None,
                                                   'coordinates': 'none',
                                                   'uncertainty': 'not reported',
                                                   'missing_behavior': 'Sentence absent does not establish an '
                                                                       'observed zero; retain absence.',
                                                   'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                                      'PARSER_CALCULATOR_PORTS_002.md',
                                                   'allowed_precisions': ['exact_for_retained_population',
                                                                          'native_rounded'],
                                                   'source_field_ids': ['legacy_pair_flag_counts'],
                                                   'native_precision_description': 'Counts below 1000 exact; '
                                                                                   '>=1000 rounded integer K/M/G '
                                                                                   'mantissa, normalized display '
                                                                                   'value in alignment_records '
                                                                                   'with native_rounded precision '
                                                                                   'and token preserved. Native '
                                                                                   'percentages one decimal. '
                                                                                   'Rounded display counts never '
                                                                                   'exact cardinality operands.',
                                                   'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                                       'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                                       'samstat_2_2_3/src/report/stat_report.c'],
                                                   'qualifications': []},
 'samstat_reported_bin_fraction': {'metric': 'samstat_reported_bin_fraction',
                                   'formats': ['samstat_html_2_2_3'],
                                   'section_key': 'samstat_mapping',
                                   'native_fields': ['2.2.3 mappingtableval[2 or4][bin0..4] including explicit '
                                                     'Total fraction'],
                                   'units': ['fraction'],
                                   'axis_kinds': ['none', 'mapq', 'native_label'],
                                   'population_keys': ['samstat_report_records',
                                                       'samstat_mapq_ge30',
                                                       'samstat_mapq_10_29',
                                                       'samstat_mapq_0_9',
                                                       'samstat_unmapped',
                                                       'samstat_report_sequences'],
                                   'meaning': 'native_normalized',
                                   'precision': 'native_rounded',
                                   'value_domain': 'number_0_1',
                                   'interpretation': 'Same individual mate column as legacy_mapping_counts',
                                   'denominator': 'Each native mate-column Total',
                                   'coordinates': 'Same bin order; Total fraction is also retained',
                                   'uncertainty': 'not reported',
                                   'missing_behavior': 'Literal -nan becomes state undefined, value null, '
                                                       'original token retained; zero count cells remain '
                                                       'available.',
                                   'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                      'PARSER_CALCULATOR_PORTS_002.md',
                                   'source_field_ids': ['legacy_mapping_fractions'],
                                   'native_precision_description': 'native_rounded: %.5f',
                                   'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                       'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                       'samstat_2_2_3/src/report/stat_report.c'],
                                   'qualifications': []},
 'samstat_reported_bin_percent': {'metric': 'samstat_reported_bin_percent',
                                  'formats': ['samstat_html_2_5_0'],
                                  'section_key': 'samstat_mapping',
                                  'native_fields': ['2.5.0 mapq table % of reads column for each bin'],
                                  'units': ['percent'],
                                  'axis_kinds': ['none', 'mapq', 'native_label'],
                                  'population_keys': ['samstat_report_records',
                                                      'samstat_mapq_ge30',
                                                      'samstat_mapq_10_29',
                                                      'samstat_mapq_0_9',
                                                      'samstat_unmapped',
                                                      'samstat_report_sequences'],
                                  'meaning': 'native_normalized',
                                  'precision': 'native_rounded',
                                  'value_domain': 'number_0_100',
                                  'interpretation': 'All primary alignment records included by report',
                                  'denominator': 'All primary report records, including unmapped. ge30 is first '
                                                 'bin / total, not divided only by mapped.',
                                  'coordinates': 'MAPQ table axes as above; cards axis none',
                                  'uncertainty': 'not reported',
                                  'missing_behavior': 'n/a -> not_measured/undefined according to zero '
                                                      'denominator source meaning; native empty-file banner has '
                                                      'no table.',
                                  'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                  'source_field_ids': ['modern_reported_mapping_percent'],
                                  'native_precision_description': 'native_rounded: one decimal',
                                  'source_evidence': ['samstat/src/collect/collect.c',
                                                      'samstat/src/htsinterface/htsglue.c',
                                                      'samstat/src/report/stat_report.c'],
                                  'qualifications': []},
 'samstat_reported_ge30_percent': {'metric': 'samstat_reported_ge30_percent',
                                   'formats': ['samstat_html_2_5_0'],
                                   'section_key': 'samstat_summary',
                                   'native_fields': ['2.5.0 strip % MAPQ >=30 dd main value'],
                                   'units': ['percent'],
                                   'axis_kinds': ['none'],
                                   'population_keys': ['samstat_report_records',
                                                       'samstat_mapq_ge30',
                                                       'samstat_mapq_10_29',
                                                       'samstat_mapq_0_9',
                                                       'samstat_unmapped',
                                                       'samstat_report_sequences'],
                                   'meaning': 'native_normalized',
                                   'precision': 'native_rounded',
                                   'value_domain': 'number_0_100',
                                   'interpretation': 'All primary alignment records included by report',
                                   'denominator': 'All primary report records, including unmapped. ge30 is first '
                                                  'bin / total, not divided only by mapped.',
                                   'coordinates': 'MAPQ table axes as above; cards axis none',
                                   'uncertainty': 'not reported',
                                   'missing_behavior': 'n/a -> not_measured/undefined according to zero '
                                                       'denominator source meaning; native empty-file banner has '
                                                       'no table.',
                                   'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                      'PARSER_CALCULATOR_PORTS_002.md',
                                   'source_field_ids': ['modern_reported_mapping_percent'],
                                   'native_precision_description': 'native_rounded: one decimal',
                                   'source_evidence': ['samstat/src/collect/collect.c',
                                                       'samstat/src/htsinterface/htsglue.c',
                                                       'samstat/src/report/stat_report.c'],
                                   'qualifications': []},
 'samstat_reported_mapped_percent': {'metric': 'samstat_reported_mapped_percent',
                                     'formats': ['samstat_html_2_5_0'],
                                     'section_key': 'samstat_summary',
                                     'native_fields': ['2.5.0 strip % mapped dd main value'],
                                     'units': ['percent'],
                                     'axis_kinds': ['none'],
                                     'population_keys': ['samstat_report_records',
                                                         'samstat_mapq_ge30',
                                                         'samstat_mapq_10_29',
                                                         'samstat_mapq_0_9',
                                                         'samstat_unmapped',
                                                         'samstat_report_sequences'],
                                     'meaning': 'native_normalized',
                                     'precision': 'native_rounded',
                                     'value_domain': 'number_0_100',
                                     'interpretation': 'All primary alignment records included by report',
                                     'denominator': 'All primary report records, including unmapped. ge30 is '
                                                    'first bin / total, not divided only by mapped.',
                                     'coordinates': 'MAPQ table axes as above; cards axis none',
                                     'uncertainty': 'not reported',
                                     'missing_behavior': 'n/a -> not_measured/undefined according to zero '
                                                         'denominator source meaning; native empty-file banner '
                                                         'has no table.',
                                     'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                        'PARSER_CALCULATOR_PORTS_002.md',
                                     'source_field_ids': ['modern_reported_mapping_percent'],
                                     'native_precision_description': 'native_rounded: one decimal',
                                     'source_evidence': ['samstat/src/collect/collect.c',
                                                         'samstat/src/htsinterface/htsglue.c',
                                                         'samstat/src/report/stat_report.c'],
                                     'qualifications': []},
 'samstat_secondary_excluded_count': {'metric': 'samstat_secondary_excluded_count',
                                      'formats': ['samstat_html_2_5_0'],
                                      'section_key': 'samstat_notes',
                                      'native_fields': ['2.5.0 footer N secondary alignments(not counted): N'],
                                      'units': ['alignment_records'],
                                      'axis_kinds': ['none'],
                                      'population_keys': ['samstat_excluded_secondary'],
                                      'meaning': 'observed_count',
                                      'precision': 'exact_for_retained_population',
                                      'value_domain': 'nonnegative_integer',
                                      'interpretation': 'Numerator is the named unavailable/excluded population. '
                                                        'Note denominator is mapped primary report records. '
                                                        'Display threshold 50 is producer configuration, not a '
                                                        'measurement. Excluded secondary/supplementary records '
                                                        'are not contributors.',
                                      'denominator': None,
                                      'coordinates': 'none',
                                      'uncertainty': 'not reported',
                                      'missing_behavior': 'Conditional note absence is not parsed as observed '
                                                          'zero; preserve unsupported/absent section if not '
                                                          'recognizable.',
                                      'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                         'PARSER_CALCULATOR_PORTS_002.md',
                                      'source_field_ids': ['modern_data_coverage_notes'],
                                      'native_precision_description': 'exact comma-separated integer tokens',
                                      'source_evidence': ['samstat/src/collect/collect.c',
                                                          'samstat/src/htsinterface/htsglue.c',
                                                          'samstat/src/report/stat_report.c',
                                                          'samstat/src/report/report_help.c'],
                                      'qualifications': []},
 'samstat_sequence_total_count': {'metric': 'samstat_sequence_total_count',
                                  'formats': ['samstat_html_2_2_3', 'samstat_html_2_5_0'],
                                  'section_key': 'samstat_summary',
                                  'native_fields': ['2.2.3 FASTX File statistics reads exact integer or (exact:N) '
                                                    'suffix',
                                                    '2.5.0 FASTA/FASTQ strip Reads: exact sublabel or unscaled '
                                                    'count',
                                                    '2.5.0 no-reads banner only with explicit FASTA/FASTQ mode'],
                                  'units': ['reads'],
                                  'axis_kinds': ['none'],
                                  'population_keys': ['samstat_report_sequences'],
                                  'meaning': 'observed_count',
                                  'precision': 'exact_for_retained_population',
                                  'value_domain': 'nonnegative_integer',
                                  'interpretation': 'Count of processed FASTA/FASTQ sequences where native mode '
                                                    'establishes FASTX. Alignment outcomes are not inferred. An '
                                                    'unknown-mode empty banner uses samstat_reported_item_count '
                                                    'instead.',
                                  'denominator': None,
                                  'coordinates': 'none none none',
                                  'uncertainty': 'not reported Original-input completeness is unknown '
                                                 'independently of HTML transfer completeness',
                                  'missing_behavior': 'No sentence/section: not_measured or malformed according '
                                                      'to retained structural evidence, never inferred from '
                                                      'density area. Bases n/a with absent sequence is not zero '
                                                      'observed bases. Empty file native banner establishes 0 '
                                                      'contributing records but no ordinary sequence/quality '
                                                      'summaries. Caller stub: failed measurement null; supported '
                                                      'HTML with truncated structural section: preserve '
                                                      'independent cells and typed partial. Exit 0 alone does not '
                                                      'prove full consumption.',
                                  'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                                  'source_field_ids': ['legacy_fastx_sequence_total',
                                                       'modern_total_counts',
                                                       'partial_and_failure'],
                                  'native_precision_description': 'exact integer token Exact integer when '
                                                                  'unscaled main token or exact comma-separated '
                                                                  'span.sub; preserve separate SI display with '
                                                                  'native_rounded Retain whatever complete '
                                                                  'numeric tokens exist; no recovery from '
                                                                  'nonexistent or truncated fields',
                                  'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                      'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                      'samstat_2_2_3/src/report/stat_report.c',
                                                      'samstat/src/collect/collect.c',
                                                      'samstat/src/htsinterface/htsglue.c',
                                                      'samstat/src/report/stat_report.c',
                                                      'caller:lib/fastq_utils.py:run_alignment'],
                                  'qualifications': ['Unmapped plot names in FASTX mode mean the reader did not '
                                                     'assign alignments; not evidence of failed alignment.',
                                                     'Use exact sublabel for arithmetic; do not reconstruct exact '
                                                     'count from SI main display alone.',
                                                     'Legacy peeking operates after whole default 10000-record '
                                                     'chunks. Modern peeking enforces exact record limit. Neither '
                                                     'prefix is a random sample.',
                                                     'Caller labels every CalledProcessError a segfault; retained '
                                                     'code 1 must not be rewritten as SIGSEGV.']},
 'samstat_soft_clipped_base_percent': {'metric': 'samstat_soft_clipped_base_percent',
                                       'formats': ['samstat_html_2_5_0'],
                                       'section_key': 'samstat_summary',
                                       'native_fields': ['strip % bases clipped'],
                                       'units': ['percent'],
                                       'axis_kinds': ['none'],
                                       'population_keys': ['samstat_report_records',
                                                           'samstat_mapq_ge30',
                                                           'samstat_mapq_10_29',
                                                           'samstat_mapq_0_9',
                                                           'samstat_unmapped',
                                                           'samstat_report_sequences'],
                                       'meaning': 'native_normalized',
                                       'precision': 'native_rounded',
                                       'value_domain': 'number_0_100',
                                       'interpretation': 'Mapped primary records with sequence; terminal soft '
                                                         'clips counted in sequenced bases',
                                       'denominator': '100*soft_clipped_bases / total full-sequence bases of '
                                                      'mapped records; not denominator of all bases if unmapped '
                                                      'present',
                                       'coordinates': 'CIGAR terminal soft clips, not hard clips; no retained '
                                                      'per-base clipping map',
                                       'uncertainty': 'not reported',
                                       'missing_behavior': 'No mapped sequence bases -> n/a.',
                                       'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                          'PARSER_CALCULATOR_PORTS_002.md',
                                       'source_field_ids': ['modern_clipping'],
                                       'native_precision_description': 'native_rounded to one decimal',
                                       'source_evidence': ['samstat/src/collect/collect.c',
                                                           'samstat/src/htsinterface/htsglue.c',
                                                           'samstat/src/report/stat_report.c'],
                                       'qualifications': []},
 'samstat_supplementary_excluded_count': {'metric': 'samstat_supplementary_excluded_count',
                                          'formats': ['samstat_html_2_5_0'],
                                          'section_key': 'samstat_notes',
                                          'native_fields': ['2.5.0 footer N supplementary alignments(not '
                                                            'counted): N'],
                                          'units': ['alignment_records'],
                                          'axis_kinds': ['none'],
                                          'population_keys': ['samstat_excluded_supplementary'],
                                          'meaning': 'observed_count',
                                          'precision': 'exact_for_retained_population',
                                          'value_domain': 'nonnegative_integer',
                                          'interpretation': 'Numerator is the named unavailable/excluded '
                                                            'population. Note denominator is mapped primary '
                                                            'report records. Display threshold 50 is producer '
                                                            'configuration, not a measurement. Excluded '
                                                            'secondary/supplementary records are not '
                                                            'contributors.',
                                          'denominator': None,
                                          'coordinates': 'none',
                                          'uncertainty': 'not reported',
                                          'missing_behavior': 'Conditional note absence is not parsed as observed '
                                                              'zero; preserve unsupported/absent section if not '
                                                              'recognizable.',
                                          'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                             'PARSER_CALCULATOR_PORTS_002.md',
                                          'source_field_ids': ['modern_data_coverage_notes'],
                                          'native_precision_description': 'exact comma-separated integer tokens',
                                          'source_evidence': ['samstat/src/collect/collect.c',
                                                              'samstat/src/htsinterface/htsglue.c',
                                                              'samstat/src/report/stat_report.c',
                                                              'samstat/src/report/report_help.c'],
                                          'qualifications': []},
 'samstat_total_base_count': {'metric': 'samstat_total_base_count',
                              'formats': ['samstat_html_2_5_0'],
                              'section_key': 'samstat_summary',
                              'native_fields': ['2.5.0 strip Bases exact span.sub integer, else unscaled N bp '
                                                'main token; n/a stays unavailable'],
                              'units': ['bases'],
                              'axis_kinds': ['none'],
                              'population_keys': ['samstat_report_records',
                                                  'samstat_mapq_ge30',
                                                  'samstat_mapq_10_29',
                                                  'samstat_mapq_0_9',
                                                  'samstat_unmapped',
                                                  'samstat_report_sequences'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Full sequence bases contributed by included primary alignment '
                                                'records or FASTX sequences, including soft clips; absent SEQ has '
                                                'no positive sequence contribution. Native n/a is not zero.',
                              'denominator': None,
                              'coordinates': 'none',
                              'uncertainty': 'not reported',
                              'missing_behavior': 'Bases n/a with absent sequence is not zero observed bases. '
                                                  'Empty file native banner establishes 0 contributing records '
                                                  'but no ordinary sequence/quality summaries.',
                              'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                              'source_field_ids': ['modern_total_counts'],
                              'native_precision_description': 'Exact integer when unscaled main token or exact '
                                                              'comma-separated span.sub; preserve separate SI '
                                                              'display with native_rounded',
                              'source_evidence': ['samstat/src/collect/collect.c',
                                                  'samstat/src/htsinterface/htsglue.c',
                                                  'samstat/src/report/stat_report.c'],
                              'qualifications': ['Use exact sublabel for arithmetic; do not reconstruct exact '
                                                 'count from SI main display alone.']},
 'samstat_uniform_length': {'metric': 'samstat_uniform_length',
                            'formats': ['samstat_html_2_5_0'],
                            'section_key': 'samstat_length',
                            'native_fields': ['2.5.0 plot1 note All N reads are LENGTH long / The read is LENGTH '
                                              'long'],
                            'units': ['bp', 'kbp', 'Mbp'],
                            'axis_kinds': ['none'],
                            'population_keys': ['samstat_report_records',
                                                'samstat_mapq_ge30',
                                                'samstat_mapq_10_29',
                                                'samstat_mapq_0_9',
                                                'samstat_unmapped',
                                                'samstat_report_sequences'],
                            'meaning': 'observed_native',
                            'precision': 'exact_for_retained_population',
                            'value_domain': 'nonnegative_number',
                            'interpretation': 'Full sequence lengths of primary records/FASTX sequences; absent '
                                              'SEQ contributes no positive length',
                            'denominator': 'Median lower quantile of length counts; N50 length threshold for half '
                                           'of total bases, native length-bin representation',
                            'coordinates': 'Length units, not reference coordinates; min/max descriptions repeat '
                                           'global extrema in each mate figure',
                            'uncertainty': 'No uncertainty interval; binning/format precision only',
                            'missing_behavior': 'No sequence -> n/a; no histogram distribution recoverable from '
                                                'SVG paths.',
                            'reviewed_source': '207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md',
                            'allowed_precisions': ['exact_for_retained_population',
                                                   'native_rounded',
                                                   'native_estimator',
                                                   'not_reported'],
                            'source_field_ids': ['modern_lengths'],
                            'native_precision_description': 'Native integer bp below display cutoff; large values '
                                                            'rounded to one decimal kb/Mb. Tilde marks lower-edge '
                                                            'storage-bin estimate, keep native_estimator and '
                                                            'original token. Never claim exact bp from rounded '
                                                            'unit display.',
                            'source_evidence': ['samstat/src/collect/collect.c',
                                                'samstat/src/htsinterface/htsglue.c',
                                                'samstat/src/report/stat_report.c',
                                                'samstat/src/plot/report_plots.c',
                                                'samstat/src/plot/report_fmt.h'],
                            'qualifications': ['Native storage bins are exact below 1000 and approximately 1% '
                                               'logarithmic above; display units create additional rounding. '
                                               'Uniform-length reports can refine native median/N50.']},
 'samstat_deletion_open_rounded_bin_mean': {'metric': 'samstat_deletion_open_rounded_bin_mean',
                                            'formats': ['samstat_html_2_2_3'],
                                            'section_key': 'samstat_deletion',
                                            'native_fields': ['2.2.3 del_R{mate}__{bin}.y; clustered rounded mean '
                                                              'of gap-opening counts'],
                                            'units': ['scaled_native_count'],
                                            'axis_kinds': ['native_label'],
                                            'population_keys': ['samstat_report_records',
                                                                'samstat_mapq_ge30',
                                                                'samstat_mapq_10_29',
                                                                'samstat_mapq_0_9',
                                                                'samstat_unmapped',
                                                                'samstat_report_sequences'],
                                            'meaning': 'native_normalized',
                                            'precision': 'native_rounded',
                                            'value_domain': 'nonnegative_integer',
                                            'interpretation': 'Error events reconstructed by native CIGAR/MD '
                                                              'processing for named mate/MAPQ stratum; mismatch '
                                                              'base labels describe read bases Clustered native '
                                                              'rounded mean per allocated position; never an '
                                                              'exact cardinality.',
                                            'denominator': 'Number of allocated positions in native cluster, not '
                                                           'records or event count. Original unclustered counts '
                                                           'are not recoverable.',
                                            'coordinates': 'Native read position after native '
                                                           'orientation/soft-clip handling, not genomic '
                                                           'coordinate. Preserve x unchanged and the soft-clip '
                                                           'defect qualification.',
                                            'uncertainty': 'not reported',
                                            'missing_behavior': 'Absent MD yields no known mismatch information; '
                                                                'zero displayed mismatch is not proof of '
                                                                'error-free alignment.',
                                            'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                               'PARSER_CALCULATOR_PORTS_002.md',
                                            'source_field_ids': ['legacy_alignment_errors'],
                                            'native_precision_description': 'exact unclustered integer token; '
                                                                            'clustered variants must use '
                                                                            'native_normalized/native_rounded '
                                                                            'metric suffix _rounded_bin_mean',
                                            'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                                'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                                'samstat_2_2_3/src/report/stat_report.c',
                                                                'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                                'samstat_2_2_3/src/plot/plot.c',
                                                                'samstat_2_2_3/src/plot/plot_interval.c',
                                                                'samstat_2_2_3/src/plot/plot_group.c'],
                                            'qualifications': ['Pinned parse_alignment advances sequence cursor '
                                                               'by one for any S operation, not its length; '
                                                               'native reconstructed mismatch assignment after '
                                                               'multi-base soft clipping can be wrong. Preserve '
                                                               'native output; no silent correction.']},
 'samstat_insertion_open_rounded_bin_mean': {'metric': 'samstat_insertion_open_rounded_bin_mean',
                                             'formats': ['samstat_html_2_2_3'],
                                             'section_key': 'samstat_insertion',
                                             'native_fields': ['2.2.3 ins_R{mate}__{bin}.y; clustered rounded '
                                                               'mean of gap-opening counts'],
                                             'units': ['scaled_native_count'],
                                             'axis_kinds': ['native_label'],
                                             'population_keys': ['samstat_report_records',
                                                                 'samstat_mapq_ge30',
                                                                 'samstat_mapq_10_29',
                                                                 'samstat_mapq_0_9',
                                                                 'samstat_unmapped',
                                                                 'samstat_report_sequences'],
                                             'meaning': 'native_normalized',
                                             'precision': 'native_rounded',
                                             'value_domain': 'nonnegative_integer',
                                             'interpretation': 'Error events reconstructed by native CIGAR/MD '
                                                               'processing for named mate/MAPQ stratum; mismatch '
                                                               'base labels describe read bases Clustered native '
                                                               'rounded mean per allocated position; never an '
                                                               'exact cardinality.',
                                             'denominator': 'Number of allocated positions in native cluster, not '
                                                            'records or event count. Original unclustered counts '
                                                            'are not recoverable.',
                                             'coordinates': 'Native read position after native '
                                                            'orientation/soft-clip handling, not genomic '
                                                            'coordinate. Preserve x unchanged and the soft-clip '
                                                            'defect qualification.',
                                             'uncertainty': 'not reported',
                                             'missing_behavior': 'Absent MD yields no known mismatch information; '
                                                                 'zero displayed mismatch is not proof of '
                                                                 'error-free alignment.',
                                             'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                                'PARSER_CALCULATOR_PORTS_002.md',
                                             'source_field_ids': ['legacy_alignment_errors'],
                                             'native_precision_description': 'exact unclustered integer token; '
                                                                             'clustered variants must use '
                                                                             'native_normalized/native_rounded '
                                                                             'metric suffix _rounded_bin_mean',
                                             'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                                 'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                                 'samstat_2_2_3/src/report/stat_report.c',
                                                                 'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                                 'samstat_2_2_3/src/plot/plot.c',
                                                                 'samstat_2_2_3/src/plot/plot_interval.c',
                                                                 'samstat_2_2_3/src/plot/plot_group.c'],
                                             'qualifications': ['Pinned parse_alignment advances sequence cursor '
                                                                'by one for any S operation, not its length; '
                                                                'native reconstructed mismatch assignment after '
                                                                'multi-base soft clipping can be wrong. Preserve '
                                                                'native output; no silent correction.']},
 'samstat_mismatch_A_rounded_bin_mean': {'metric': 'samstat_mismatch_A_rounded_bin_mean',
                                         'formats': ['samstat_html_2_2_3'],
                                         'section_key': 'samstat_mismatch',
                                         'native_fields': ['2.2.3 mis_R{mate}_{bin}_A.y; read-base symbolA; '
                                                           'clustered rounded native mean'],
                                         'units': ['scaled_native_count'],
                                         'axis_kinds': ['native_label'],
                                         'population_keys': ['samstat_report_records',
                                                             'samstat_mapq_ge30',
                                                             'samstat_mapq_10_29',
                                                             'samstat_mapq_0_9',
                                                             'samstat_unmapped',
                                                             'samstat_report_sequences'],
                                         'meaning': 'native_normalized',
                                         'precision': 'native_rounded',
                                         'value_domain': 'nonnegative_integer',
                                         'interpretation': 'Error events reconstructed by native CIGAR/MD '
                                                           'processing for named mate/MAPQ stratum; mismatch base '
                                                           'labels describe read bases Clustered native rounded '
                                                           'mean per allocated position; never an exact '
                                                           'cardinality.',
                                         'denominator': 'Number of allocated positions in native cluster, not '
                                                        'records or event count. Original unclustered counts are '
                                                        'not recoverable.',
                                         'coordinates': 'Native read position after native orientation/soft-clip '
                                                        'handling, not genomic coordinate. Preserve x unchanged '
                                                        'and the soft-clip defect qualification.',
                                         'uncertainty': 'not reported',
                                         'missing_behavior': 'Absent MD yields no known mismatch information; '
                                                             'zero displayed mismatch is not proof of error-free '
                                                             'alignment.',
                                         'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                            'PARSER_CALCULATOR_PORTS_002.md',
                                         'source_field_ids': ['legacy_alignment_errors'],
                                         'native_precision_description': 'exact unclustered integer token; '
                                                                         'clustered variants must use '
                                                                         'native_normalized/native_rounded metric '
                                                                         'suffix _rounded_bin_mean',
                                         'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                             'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                             'samstat_2_2_3/src/report/stat_report.c',
                                                             'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                             'samstat_2_2_3/src/plot/plot.c',
                                                             'samstat_2_2_3/src/plot/plot_interval.c',
                                                             'samstat_2_2_3/src/plot/plot_group.c'],
                                         'qualifications': ['Pinned parse_alignment advances sequence cursor by '
                                                            'one for any S operation, not its length; native '
                                                            'reconstructed mismatch assignment after multi-base '
                                                            'soft clipping can be wrong. Preserve native output; '
                                                            'no silent correction.']},
 'samstat_mismatch_C_rounded_bin_mean': {'metric': 'samstat_mismatch_C_rounded_bin_mean',
                                         'formats': ['samstat_html_2_2_3'],
                                         'section_key': 'samstat_mismatch',
                                         'native_fields': ['2.2.3 mis_R{mate}_{bin}_C.y; read-base symbolC; '
                                                           'clustered rounded native mean'],
                                         'units': ['scaled_native_count'],
                                         'axis_kinds': ['native_label'],
                                         'population_keys': ['samstat_report_records',
                                                             'samstat_mapq_ge30',
                                                             'samstat_mapq_10_29',
                                                             'samstat_mapq_0_9',
                                                             'samstat_unmapped',
                                                             'samstat_report_sequences'],
                                         'meaning': 'native_normalized',
                                         'precision': 'native_rounded',
                                         'value_domain': 'nonnegative_integer',
                                         'interpretation': 'Error events reconstructed by native CIGAR/MD '
                                                           'processing for named mate/MAPQ stratum; mismatch base '
                                                           'labels describe read bases Clustered native rounded '
                                                           'mean per allocated position; never an exact '
                                                           'cardinality.',
                                         'denominator': 'Number of allocated positions in native cluster, not '
                                                        'records or event count. Original unclustered counts are '
                                                        'not recoverable.',
                                         'coordinates': 'Native read position after native orientation/soft-clip '
                                                        'handling, not genomic coordinate. Preserve x unchanged '
                                                        'and the soft-clip defect qualification.',
                                         'uncertainty': 'not reported',
                                         'missing_behavior': 'Absent MD yields no known mismatch information; '
                                                             'zero displayed mismatch is not proof of error-free '
                                                             'alignment.',
                                         'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                            'PARSER_CALCULATOR_PORTS_002.md',
                                         'source_field_ids': ['legacy_alignment_errors'],
                                         'native_precision_description': 'exact unclustered integer token; '
                                                                         'clustered variants must use '
                                                                         'native_normalized/native_rounded metric '
                                                                         'suffix _rounded_bin_mean',
                                         'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                             'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                             'samstat_2_2_3/src/report/stat_report.c',
                                                             'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                             'samstat_2_2_3/src/plot/plot.c',
                                                             'samstat_2_2_3/src/plot/plot_interval.c',
                                                             'samstat_2_2_3/src/plot/plot_group.c'],
                                         'qualifications': ['Pinned parse_alignment advances sequence cursor by '
                                                            'one for any S operation, not its length; native '
                                                            'reconstructed mismatch assignment after multi-base '
                                                            'soft clipping can be wrong. Preserve native output; '
                                                            'no silent correction.']},
 'samstat_mismatch_G_rounded_bin_mean': {'metric': 'samstat_mismatch_G_rounded_bin_mean',
                                         'formats': ['samstat_html_2_2_3'],
                                         'section_key': 'samstat_mismatch',
                                         'native_fields': ['2.2.3 mis_R{mate}_{bin}_G.y; read-base symbolG; '
                                                           'clustered rounded native mean'],
                                         'units': ['scaled_native_count'],
                                         'axis_kinds': ['native_label'],
                                         'population_keys': ['samstat_report_records',
                                                             'samstat_mapq_ge30',
                                                             'samstat_mapq_10_29',
                                                             'samstat_mapq_0_9',
                                                             'samstat_unmapped',
                                                             'samstat_report_sequences'],
                                         'meaning': 'native_normalized',
                                         'precision': 'native_rounded',
                                         'value_domain': 'nonnegative_integer',
                                         'interpretation': 'Error events reconstructed by native CIGAR/MD '
                                                           'processing for named mate/MAPQ stratum; mismatch base '
                                                           'labels describe read bases Clustered native rounded '
                                                           'mean per allocated position; never an exact '
                                                           'cardinality.',
                                         'denominator': 'Number of allocated positions in native cluster, not '
                                                        'records or event count. Original unclustered counts are '
                                                        'not recoverable.',
                                         'coordinates': 'Native read position after native orientation/soft-clip '
                                                        'handling, not genomic coordinate. Preserve x unchanged '
                                                        'and the soft-clip defect qualification.',
                                         'uncertainty': 'not reported',
                                         'missing_behavior': 'Absent MD yields no known mismatch information; '
                                                             'zero displayed mismatch is not proof of error-free '
                                                             'alignment.',
                                         'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                            'PARSER_CALCULATOR_PORTS_002.md',
                                         'source_field_ids': ['legacy_alignment_errors'],
                                         'native_precision_description': 'exact unclustered integer token; '
                                                                         'clustered variants must use '
                                                                         'native_normalized/native_rounded metric '
                                                                         'suffix _rounded_bin_mean',
                                         'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                             'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                             'samstat_2_2_3/src/report/stat_report.c',
                                                             'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                             'samstat_2_2_3/src/plot/plot.c',
                                                             'samstat_2_2_3/src/plot/plot_interval.c',
                                                             'samstat_2_2_3/src/plot/plot_group.c'],
                                         'qualifications': ['Pinned parse_alignment advances sequence cursor by '
                                                            'one for any S operation, not its length; native '
                                                            'reconstructed mismatch assignment after multi-base '
                                                            'soft clipping can be wrong. Preserve native output; '
                                                            'no silent correction.']},
 'samstat_mismatch_N_rounded_bin_mean': {'metric': 'samstat_mismatch_N_rounded_bin_mean',
                                         'formats': ['samstat_html_2_2_3'],
                                         'section_key': 'samstat_mismatch',
                                         'native_fields': ['2.2.3 mis_R{mate}_{bin}_N.y; read-base symbolN; '
                                                           'clustered rounded native mean'],
                                         'units': ['scaled_native_count'],
                                         'axis_kinds': ['native_label'],
                                         'population_keys': ['samstat_report_records',
                                                             'samstat_mapq_ge30',
                                                             'samstat_mapq_10_29',
                                                             'samstat_mapq_0_9',
                                                             'samstat_unmapped',
                                                             'samstat_report_sequences'],
                                         'meaning': 'native_normalized',
                                         'precision': 'native_rounded',
                                         'value_domain': 'nonnegative_integer',
                                         'interpretation': 'Error events reconstructed by native CIGAR/MD '
                                                           'processing for named mate/MAPQ stratum; mismatch base '
                                                           'labels describe read bases Clustered native rounded '
                                                           'mean per allocated position; never an exact '
                                                           'cardinality.',
                                         'denominator': 'Number of allocated positions in native cluster, not '
                                                        'records or event count. Original unclustered counts are '
                                                        'not recoverable.',
                                         'coordinates': 'Native read position after native orientation/soft-clip '
                                                        'handling, not genomic coordinate. Preserve x unchanged '
                                                        'and the soft-clip defect qualification.',
                                         'uncertainty': 'not reported',
                                         'missing_behavior': 'Absent MD yields no known mismatch information; '
                                                             'zero displayed mismatch is not proof of error-free '
                                                             'alignment.',
                                         'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                            'PARSER_CALCULATOR_PORTS_002.md',
                                         'source_field_ids': ['legacy_alignment_errors'],
                                         'native_precision_description': 'exact unclustered integer token; '
                                                                         'clustered variants must use '
                                                                         'native_normalized/native_rounded metric '
                                                                         'suffix _rounded_bin_mean',
                                         'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                             'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                             'samstat_2_2_3/src/report/stat_report.c',
                                                             'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                             'samstat_2_2_3/src/plot/plot.c',
                                                             'samstat_2_2_3/src/plot/plot_interval.c',
                                                             'samstat_2_2_3/src/plot/plot_group.c'],
                                         'qualifications': ['Pinned parse_alignment advances sequence cursor by '
                                                            'one for any S operation, not its length; native '
                                                            'reconstructed mismatch assignment after multi-base '
                                                            'soft clipping can be wrong. Preserve native output; '
                                                            'no silent correction.']},
 'samstat_mismatch_T_rounded_bin_mean': {'metric': 'samstat_mismatch_T_rounded_bin_mean',
                                         'formats': ['samstat_html_2_2_3'],
                                         'section_key': 'samstat_mismatch',
                                         'native_fields': ['2.2.3 mis_R{mate}_{bin}_T.y; read-base symbolT; '
                                                           'clustered rounded native mean'],
                                         'units': ['scaled_native_count'],
                                         'axis_kinds': ['native_label'],
                                         'population_keys': ['samstat_report_records',
                                                             'samstat_mapq_ge30',
                                                             'samstat_mapq_10_29',
                                                             'samstat_mapq_0_9',
                                                             'samstat_unmapped',
                                                             'samstat_report_sequences'],
                                         'meaning': 'native_normalized',
                                         'precision': 'native_rounded',
                                         'value_domain': 'nonnegative_integer',
                                         'interpretation': 'Error events reconstructed by native CIGAR/MD '
                                                           'processing for named mate/MAPQ stratum; mismatch base '
                                                           'labels describe read bases Clustered native rounded '
                                                           'mean per allocated position; never an exact '
                                                           'cardinality.',
                                         'denominator': 'Number of allocated positions in native cluster, not '
                                                        'records or event count. Original unclustered counts are '
                                                        'not recoverable.',
                                         'coordinates': 'Native read position after native orientation/soft-clip '
                                                        'handling, not genomic coordinate. Preserve x unchanged '
                                                        'and the soft-clip defect qualification.',
                                         'uncertainty': 'not reported',
                                         'missing_behavior': 'Absent MD yields no known mismatch information; '
                                                             'zero displayed mismatch is not proof of error-free '
                                                             'alignment.',
                                         'reviewed_source': '207 NATIVE_FIELDS_002.json / '
                                                            'PARSER_CALCULATOR_PORTS_002.md',
                                         'source_field_ids': ['legacy_alignment_errors'],
                                         'native_precision_description': 'exact unclustered integer token; '
                                                                         'clustered variants must use '
                                                                         'native_normalized/native_rounded metric '
                                                                         'suffix _rounded_bin_mean',
                                         'source_evidence': ['samstat_2_2_3/src/collect/collect.c',
                                                             'samstat_2_2_3/src/htsinterface/htsglue.c',
                                                             'samstat_2_2_3/src/report/stat_report.c',
                                                             'samstat_2_2_3/src/sambamparse/sam_bam_parse.c',
                                                             'samstat_2_2_3/src/plot/plot.c',
                                                             'samstat_2_2_3/src/plot/plot_interval.c',
                                                             'samstat_2_2_3/src/plot/plot_group.c'],
                                         'qualifications': ['Pinned parse_alignment advances sequence cursor by '
                                                            'one for any S operation, not its length; native '
                                                            'reconstructed mismatch assignment after multi-base '
                                                            'soft clipping can be wrong. Preserve native output; '
                                                            'no silent correction.']},
 'samstat_reported_item_count': {'metric': 'samstat_reported_item_count',
                                 'formats': ['samstat_html_2_5_0'],
                                 'section_key': 'samstat_summary',
                                 'native_fields': ['This file contains no reads. banner with native input-mode '
                                                   'label absent'],
                                 'units': ['native_count'],
                                 'axis_kinds': ['none'],
                                 'population_keys': [],
                                 'meaning': 'observed_count',
                                 'precision': 'exact_for_retained_population',
                                 'value_domain': 'nonnegative_integer',
                                 'interpretation': 'Explicit zero contributing items asserted by the native '
                                                   'no-reads banner. Sequence versus alignment item type remains '
                                                   'unknown; null population. Not a FASTQ/molecule/pair count.',
                                 'denominator': None,
                                 'coordinates': 'none',
                                 'uncertainty': 'not_reported',
                                 'missing_behavior': 'Only emitted for the recognized no-reads banner with absent '
                                                     'native input-mode label. Source_row_absent plus '
                                                     'native_execution_evidence requirement preserves the missing '
                                                     'input-kind interpretation. Never a mapping or sequence '
                                                     'calculator operand.',
                                 'reviewed_source': '212 SOURCE_CLARIFICATION_002.md;207 '
                                                    'native2_5_0/empty.fastq.samstat.html and stat_report.c '
                                                    'input_format_name/stat_report'}}

SAMSTAT_COMPONENTS = {'samstat_report_mapped_record_fraction': {'metric': 'samstat_report_mapped_record_fraction',
                                           'method': 'samstat_report_mapping_v1',
                                           'formula': '(T-U)/T',
                                           'input_fields': ['selected same-document/version disjoint '
                                                            'samstat_report_records populations',
                                                            'four exact samstat_alignment_bin_count operands per '
                                                            'population: ge30,10_29,0_9,unmapped',
                                                            'optional native samstat_alignment_total_count as '
                                                            'consistency check'],
                                           'units': ['fraction'],
                                           'meaning': 'native_report_derived',
                                           'uncertainty': 'not_estimated',
                                           'population': 'Contributing primary records in2.5.0; '
                                                         'secondary-excluded, supplementary-retained records '
                                                         'in2.2.3. No FASTQ/molecule/pair inference.',
                                           'denominator': 'T=sum of four exact native count bins across selected '
                                                          'nonoverlapping strata; U=unmapped sum; H=ge30 sum '
                                                          'including MAPQ255.',
                                           'requirements': 'One or two explicitly selected strata from one '
                                                           'supported alignment-mode document/version; complete '
                                                           'unique exact count bins; no all+mate overlap; '
                                                           'optional total must agree.',
                                           'missing_behavior': 'Zero denominator undefined; absent/truncated bin '
                                                               'missing/truncated; conflicting populations/counts '
                                                               'incompatible; prefix or partial document yields '
                                                               'partial; unproved input scope remains '
                                                               'report-population-only.',
                                           'source_contract': '207 PARSER_CALCULATOR_PORTS_002.md section6; '
                                                              'calculator separately implemented'},
 'samstat_report_ge30_record_fraction': {'metric': 'samstat_report_ge30_record_fraction',
                                         'method': 'samstat_report_mapping_v1',
                                         'formula': '(H)/T',
                                         'input_fields': ['selected same-document/version disjoint '
                                                          'samstat_report_records populations',
                                                          'four exact samstat_alignment_bin_count operands per '
                                                          'population: ge30,10_29,0_9,unmapped',
                                                          'optional native samstat_alignment_total_count as '
                                                          'consistency check'],
                                         'units': ['fraction'],
                                         'meaning': 'native_report_derived',
                                         'uncertainty': 'not_estimated',
                                         'population': 'Contributing primary records in2.5.0; secondary-excluded, '
                                                       'supplementary-retained records in2.2.3. No '
                                                       'FASTQ/molecule/pair inference.',
                                         'denominator': 'T=sum of four exact native count bins across selected '
                                                        'nonoverlapping strata; U=unmapped sum; H=ge30 sum '
                                                        'including MAPQ255.',
                                         'requirements': 'One or two explicitly selected strata from one '
                                                         'supported alignment-mode document/version; complete '
                                                         'unique exact count bins; no all+mate overlap; optional '
                                                         'total must agree.',
                                         'missing_behavior': 'Zero denominator undefined; absent/truncated bin '
                                                             'missing/truncated; conflicting populations/counts '
                                                             'incompatible; prefix or partial document yields '
                                                             'partial; unproved input scope remains '
                                                             'report-population-only.',
                                         'source_contract': '207 PARSER_CALCULATOR_PORTS_002.md section6; '
                                                            'calculator separately implemented'}}
