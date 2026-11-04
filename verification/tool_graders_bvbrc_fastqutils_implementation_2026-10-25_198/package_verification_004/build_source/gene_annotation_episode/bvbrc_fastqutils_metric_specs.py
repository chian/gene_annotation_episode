"""Fixed numerical meanings, units and source descriptions; no formula evaluator.

Copied from the reviewed62 native and17 component registries. Scientific
calculations remain ordinary functions in their separately owned modules.
"""
from copy import deepcopy
from .bvbrc_fastqutils_contracts import FastqUtilsContractError

_METRICS = {'fastq_read_count': {'metric': 'fastq_read_count',
                      'formats': ['fastq'],
                      'section_key': 'fastq_summary',
                      'native_fields': ['validated record count'],
                      'units': ['reads'],
                      'axis_kinds': ['none'],
                      'population_keys': ['fastq_reads'],
                      'meaning': 'observed_count',
                      'precision': 'exact_for_retained_population',
                      'value_domain': 'nonnegative_integer',
                      'interpretation': 'Count complete validated FASTQ records, including zero '
                                        'for a complete empty file.',
                      'denominator': None,
                      'coordinates': 'not_applicable',
                      'uncertainty': 'not_reported',
                      'missing_behavior': 'Preserve native token and explicit state; absent row is '
                                          'not numerical zero. Partial populations retain partial '
                                          'counts; no whole-population inference.',
                      'reviewed_source': 'FASTQ records supplied in full;193 CONTRACT_001 '
                                         'sections4-6'},
 'fastq_base_count': {'metric': 'fastq_base_count',
                      'formats': ['fastq'],
                      'section_key': 'fastq_summary',
                      'native_fields': ['sequence character count'],
                      'units': ['bases'],
                      'axis_kinds': ['none'],
                      'population_keys': ['fastq_bases'],
                      'meaning': 'observed_count',
                      'precision': 'exact_for_retained_population',
                      'value_domain': 'nonnegative_integer',
                      'interpretation': 'Count all supplied sequence symbols; invalid symbols '
                                        'remain separately counted.',
                      'denominator': None,
                      'coordinates': 'not_applicable',
                      'uncertainty': 'not_reported',
                      'missing_behavior': 'Preserve native token and explicit state; absent row is '
                                          'not numerical zero. Partial populations retain partial '
                                          'counts; no whole-population inference.',
                      'reviewed_source': 'FASTQ records supplied in full;193 CONTRACT_001 '
                                         'sections4-6'},
 'fastq_symbol_count': {'metric': 'fastq_symbol_count',
                        'formats': ['fastq'],
                        'section_key': 'fastq_summary',
                        'native_fields': ['A', 'C', 'G', 'T', 'N', 'other_iupac', 'invalid'],
                        'units': ['bases'],
                        'axis_kinds': ['symbol'],
                        'population_keys': ['fastq_bases'],
                        'meaning': 'observed_count',
                        'precision': 'exact_for_retained_population',
                        'value_domain': 'nonnegative_integer',
                        'interpretation': 'Case-insensitive A/C/G/T/N counts; other IUPAC excludes '
                                          'N. Invalid symbols are not silently assigned to '
                                          'ambiguity.',
                        'denominator': None,
                        'coordinates': 'not_applicable',
                        'uncertainty': 'not_reported',
                        'missing_behavior': 'Preserve native token and explicit state; absent row '
                                            'is not numerical zero. Partial populations retain '
                                            'partial counts; no whole-population inference.',
                        'reviewed_source': 'FASTQ records supplied in full;193 CONTRACT_001 '
                                           'sections4-6'},
 'fastq_min_length': {'metric': 'fastq_min_length',
                      'formats': ['fastq'],
                      'section_key': 'fastq_summary',
                      'native_fields': ['minimum retained sequence length'],
                      'units': ['bases'],
                      'axis_kinds': ['none'],
                      'population_keys': ['fastq_reads'],
                      'meaning': 'observed_count',
                      'precision': 'exact_for_retained_population',
                      'value_domain': 'nonnegative_integer',
                      'interpretation': 'Observed extrema over validated reads; empty population '
                                        'yields undefined/null, not zero-length read.',
                      'denominator': None,
                      'coordinates': 'not_applicable',
                      'uncertainty': 'not_reported',
                      'missing_behavior': 'Preserve native token and explicit state; absent row is '
                                          'not numerical zero. Partial populations retain partial '
                                          'counts; no whole-population inference.',
                      'reviewed_source': 'FASTQ records supplied in full;193 CONTRACT_001 '
                                         'sections4-6'},
 'fastq_max_length': {'metric': 'fastq_max_length',
                      'formats': ['fastq'],
                      'section_key': 'fastq_summary',
                      'native_fields': ['maximum retained sequence length'],
                      'units': ['bases'],
                      'axis_kinds': ['none'],
                      'population_keys': ['fastq_reads'],
                      'meaning': 'observed_count',
                      'precision': 'exact_for_retained_population',
                      'value_domain': 'nonnegative_integer',
                      'interpretation': 'Observed extrema over validated reads; empty population '
                                        'yields undefined/null, not zero-length read.',
                      'denominator': None,
                      'coordinates': 'not_applicable',
                      'uncertainty': 'not_reported',
                      'missing_behavior': 'Preserve native token and explicit state; absent row is '
                                          'not numerical zero. Partial populations retain partial '
                                          'counts; no whole-population inference.',
                      'reviewed_source': 'FASTQ records supplied in full;193 CONTRACT_001 '
                                         'sections4-6'},
 'fastq_length_histogram_count': {'metric': 'fastq_length_histogram_count',
                                  'formats': ['fastq'],
                                  'section_key': 'fastq_summary',
                                  'native_fields': ['exact sequence length', 'read count'],
                                  'units': ['reads'],
                                  'axis_kinds': ['length_closed'],
                                  'population_keys': ['fastq_reads'],
                                  'meaning': 'observed_count',
                                  'precision': 'exact_for_retained_population',
                                  'value_domain': 'nonnegative_integer',
                                  'interpretation': 'Singleton length bins contain actual read '
                                                    'counts.',
                                  'denominator': None,
                                  'coordinates': 'closed native axis bins; BAM positions '
                                                 'separately zero-based',
                                  'uncertainty': 'not_reported',
                                  'missing_behavior': 'Preserve native token and explicit state; '
                                                      'absent row is not numerical zero. Partial '
                                                      'populations retain partial counts; no '
                                                      'whole-population inference.',
                                  'reviewed_source': 'FASTQ records supplied in full;193 '
                                                     'CONTRACT_001 sections4-6'},
 'quality_character_count': {'metric': 'quality_character_count',
                             'formats': ['fastq'],
                             'section_key': 'fastq_summary',
                             'native_fields': ['ASCII quality symbol', 'base count'],
                             'units': ['bases'],
                             'axis_kinds': ['quality_ascii'],
                             'population_keys': ['fastq_quality_characters'],
                             'meaning': 'observed_count',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Counts raw quality ASCII symbols without assuming '
                                               'an encoding.',
                             'denominator': None,
                             'coordinates': 'not_applicable',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Preserve native token and explicit state; absent '
                                                 'row is not numerical zero. Partial populations '
                                                 'retain partial counts; no whole-population '
                                                 'inference.',
                             'reviewed_source': 'FASTQ records supplied in full;193 CONTRACT_001 '
                                                'sections4-6'},
 'phred_histogram_count': {'metric': 'phred_histogram_count',
                           'formats': ['sam_1_6', 'bam_1'],
                           'section_key': 'bam_summary',
                           'native_fields': ['native numeric Phred quality', 'base count'],
                           'units': ['bases'],
                           'axis_kinds': ['quality_score'],
                           'population_keys': ['bam_quality_bases'],
                           'meaning': 'observed_count',
                           'precision': 'exact_for_retained_population',
                           'value_domain': 'nonnegative_integer',
                           'interpretation': 'BAM numeric qualities or SAM QUAL decoded using the '
                                             'SAM-specified Phred+33 representation; missing '
                                             'qualities retained separately, never 255 as Q.',
                           'denominator': None,
                           'coordinates': 'not_applicable',
                           'uncertainty': 'not_reported',
                           'missing_behavior': 'Preserve native token and explicit state; absent '
                                               'row is not numerical zero. Partial populations '
                                               'retain partial counts; no whole-population '
                                               'inference.',
                           'reviewed_source': 'sources/hts-specs/SAMv1.tex mandatory fields and '
                                              'BAM quality representation'},
 'verified_pair_count': {'metric': 'verified_pair_count',
                         'formats': ['fastq'],
                         'section_key': 'fastq_summary',
                         'native_fields': ['explicit PairDeclaration',
                                           'actual unique paired key correspondence'],
                         'units': ['pairs'],
                         'axis_kinds': ['none'],
                         'population_keys': ['verified_read_pairs'],
                         'meaning': 'observed_count',
                         'precision': 'exact_for_retained_population',
                         'value_domain': 'nonnegative_integer',
                         'interpretation': 'C metadata structural join count after explicit '
                                           'mate/key declaration and actual one-to-one record '
                                           'matching; never halve read counts.',
                         'denominator': None,
                         'coordinates': 'not_applicable',
                         'uncertainty': 'not_reported',
                         'missing_behavior': 'Preserve native token and explicit state; absent row '
                                             'is not numerical zero. Partial populations retain '
                                             'partial counts; no whole-population inference.',
                         'reviewed_source': '193 CONTRACT_001 pairing requirements;195 PORTS_002 '
                                            'join_ref/Metadata.measurements'},
 'fastqc_total_sequences': {'metric': 'fastqc_total_sequences',
                            'formats': ['fastqc_data_0_12_1',
                                        'fastqc_zip_0_12_1',
                                        'fastqc_html_0_12_1'],
                            'section_key': 'fastqc_basic_statistics',
                            'native_fields': ['Total Sequences'],
                            'units': ['reads'],
                            'axis_kinds': ['none'],
                            'population_keys': ['fastqc_module'],
                            'meaning': 'observed_count',
                            'precision': 'exact_for_retained_population',
                            'value_domain': 'nonnegative_integer',
                            'interpretation': 'Native total excludes filtered sequences; flagged '
                                              'count is separately retained.',
                            'denominator': None,
                            'coordinates': 'not_applicable',
                            'uncertainty': 'not_reported',
                            'missing_behavior': 'Preserve native token and explicit state; absent '
                                                'row is not numerical zero. Partial populations '
                                                'retain partial counts; no whole-population '
                                                'inference.',
                            'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/BasicStats.java'},
 'fastqc_flagged_sequences': {'metric': 'fastqc_flagged_sequences',
                              'formats': ['fastqc_data_0_12_1',
                                          'fastqc_zip_0_12_1',
                                          'fastqc_html_0_12_1'],
                              'section_key': 'fastqc_basic_statistics',
                              'native_fields': ['Sequences flagged as poor quality'],
                              'units': ['reads'],
                              'axis_kinds': ['none'],
                              'population_keys': ['fastqc_module'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Native total excludes filtered sequences; flagged '
                                                'count is separately retained.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Preserve native token and explicit state; '
                                                  'absent row is not numerical zero. Partial '
                                                  'populations retain partial counts; no '
                                                  'whole-population inference.',
                              'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/BasicStats.java'},
 'fastqc_total_bases_display': {'metric': 'fastqc_total_bases_display',
                                'formats': ['fastqc_data_0_12_1',
                                            'fastqc_zip_0_12_1',
                                            'fastqc_html_0_12_1'],
                                'section_key': 'fastqc_basic_statistics',
                                'native_fields': ['Total Bases lexical quantity and suffix'],
                                'units': ['bp', 'kbp', 'Mbp', 'Gbp'],
                                'axis_kinds': ['none'],
                                'population_keys': ['fastqc_module'],
                                'meaning': 'observed_native',
                                'precision': 'native_truncated_display',
                                'value_domain': 'nonnegative_number',
                                'interpretation': 'Store displayed number with displayed unit and '
                                                  'exact token. It is not an exact base '
                                                  'denominator.',
                                'denominator': None,
                                'coordinates': 'not_applicable',
                                'uncertainty': 'not_reported',
                                'missing_behavior': 'Preserve native token and explicit state; '
                                                    'absent row is not numerical zero. Partial '
                                                    'populations retain partial counts; no '
                                                    'whole-population inference.',
                                'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/BasicStats.java'},
 'fastqc_min_length': {'metric': 'fastqc_min_length',
                       'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1', 'fastqc_html_0_12_1'],
                       'section_key': 'fastqc_basic_statistics',
                       'native_fields': ['Sequence length lower'],
                       'units': ['bases'],
                       'axis_kinds': ['none'],
                       'population_keys': ['fastqc_module'],
                       'meaning': 'observed_native',
                       'precision': 'exact_for_retained_population',
                       'value_domain': 'nonnegative_integer',
                       'interpretation': 'Native displayed read-length endpoints; keep '
                                         'singleton/range meaning.',
                       'denominator': None,
                       'coordinates': 'not_applicable',
                       'uncertainty': 'not_reported',
                       'missing_behavior': 'Preserve native token and explicit state; absent row '
                                           'is not numerical zero. Partial populations retain '
                                           'partial counts; no whole-population inference.',
                       'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/BasicStats.java'},
 'fastqc_max_length': {'metric': 'fastqc_max_length',
                       'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1', 'fastqc_html_0_12_1'],
                       'section_key': 'fastqc_basic_statistics',
                       'native_fields': ['Sequence length upper'],
                       'units': ['bases'],
                       'axis_kinds': ['none'],
                       'population_keys': ['fastqc_module'],
                       'meaning': 'observed_native',
                       'precision': 'exact_for_retained_population',
                       'value_domain': 'nonnegative_integer',
                       'interpretation': 'Native displayed read-length endpoints; keep '
                                         'singleton/range meaning.',
                       'denominator': None,
                       'coordinates': 'not_applicable',
                       'uncertainty': 'not_reported',
                       'missing_behavior': 'Preserve native token and explicit state; absent row '
                                           'is not numerical zero. Partial populations retain '
                                           'partial counts; no whole-population inference.',
                       'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/BasicStats.java'},
 'fastqc_gc_percent': {'metric': 'fastqc_gc_percent',
                       'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1', 'fastqc_html_0_12_1'],
                       'section_key': 'fastqc_basic_statistics',
                       'native_fields': ['%GC'],
                       'units': ['percent'],
                       'axis_kinds': ['none'],
                       'population_keys': ['fastqc_module'],
                       'meaning': 'native_normalized',
                       'precision': 'native_truncated_display',
                       'value_domain': 'integer_0_100',
                       'interpretation': 'Native floor(100*(G+C)/(A+C+G+T)); source '
                                         'zero-denominator fallback0 is qualified, not a true GC '
                                         'estimate.',
                       'denominator': 'native A+C+G+T; unavailable as exact count in report',
                       'coordinates': 'not_applicable',
                       'uncertainty': 'not_reported',
                       'missing_behavior': 'Preserve native token and explicit state; absent row '
                                           'is not numerical zero. Partial populations retain '
                                           'partial counts; no whole-population inference.',
                       'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/BasicStats.java'},
 'fastqc_base_quality_mean': {'metric': 'fastqc_base_quality_mean',
                              'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                              'section_key': 'fastqc_per_base_quality',
                              'native_fields': ['Mean'],
                              'units': ['phred'],
                              'axis_kinds': ['base_closed_1'],
                              'population_keys': ['fastqc_module'],
                              'meaning': 'observed_native',
                              'precision': 'not_reported',
                              'value_domain': 'finite_number',
                              'interpretation': 'Grouped means average per-position means; grouped '
                                                'quantiles average source per-position quantiles '
                                                'with >100 observations. Not pooled quantiles or a '
                                                'per-base score histogram.',
                              'denominator': None,
                              'coordinates': 'closed 1-based native bins',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Native NaN/nonfinite -> null explicit '
                                                  'nonfinite_native; no graph recovery from HTML.',
                              'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerBaseQualityScores.java'},
 'fastqc_base_quality_median': {'metric': 'fastqc_base_quality_median',
                                'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                'section_key': 'fastqc_per_base_quality',
                                'native_fields': ['Median'],
                                'units': ['phred'],
                                'axis_kinds': ['base_closed_1'],
                                'population_keys': ['fastqc_module'],
                                'meaning': 'observed_native',
                                'precision': 'not_reported',
                                'value_domain': 'finite_number',
                                'interpretation': 'Grouped means average per-position means; '
                                                  'grouped quantiles average source per-position '
                                                  'quantiles with >100 observations. Not pooled '
                                                  'quantiles or a per-base score histogram.',
                                'denominator': None,
                                'coordinates': 'closed 1-based native bins',
                                'uncertainty': 'not_reported',
                                'missing_behavior': 'Native NaN/nonfinite -> null explicit '
                                                    'nonfinite_native; no graph recovery from '
                                                    'HTML.',
                                'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerBaseQualityScores.java'},
 'fastqc_base_quality_lower_quartile': {'metric': 'fastqc_base_quality_lower_quartile',
                                        'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                        'section_key': 'fastqc_per_base_quality',
                                        'native_fields': ['Lower Quartile'],
                                        'units': ['phred'],
                                        'axis_kinds': ['base_closed_1'],
                                        'population_keys': ['fastqc_module'],
                                        'meaning': 'observed_native',
                                        'precision': 'not_reported',
                                        'value_domain': 'finite_number',
                                        'interpretation': 'Grouped means average per-position '
                                                          'means; grouped quantiles average source '
                                                          'per-position quantiles with >100 '
                                                          'observations. Not pooled quantiles or a '
                                                          'per-base score histogram.',
                                        'denominator': None,
                                        'coordinates': 'closed 1-based native bins',
                                        'uncertainty': 'not_reported',
                                        'missing_behavior': 'Native NaN/nonfinite -> null explicit '
                                                            'nonfinite_native; no graph recovery '
                                                            'from HTML.',
                                        'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerBaseQualityScores.java'},
 'fastqc_base_quality_upper_quartile': {'metric': 'fastqc_base_quality_upper_quartile',
                                        'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                        'section_key': 'fastqc_per_base_quality',
                                        'native_fields': ['Upper Quartile'],
                                        'units': ['phred'],
                                        'axis_kinds': ['base_closed_1'],
                                        'population_keys': ['fastqc_module'],
                                        'meaning': 'observed_native',
                                        'precision': 'not_reported',
                                        'value_domain': 'finite_number',
                                        'interpretation': 'Grouped means average per-position '
                                                          'means; grouped quantiles average source '
                                                          'per-position quantiles with >100 '
                                                          'observations. Not pooled quantiles or a '
                                                          'per-base score histogram.',
                                        'denominator': None,
                                        'coordinates': 'closed 1-based native bins',
                                        'uncertainty': 'not_reported',
                                        'missing_behavior': 'Native NaN/nonfinite -> null explicit '
                                                            'nonfinite_native; no graph recovery '
                                                            'from HTML.',
                                        'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerBaseQualityScores.java'},
 'fastqc_base_quality_p10': {'metric': 'fastqc_base_quality_p10',
                             'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                             'section_key': 'fastqc_per_base_quality',
                             'native_fields': ['10th Percentile'],
                             'units': ['phred'],
                             'axis_kinds': ['base_closed_1'],
                             'population_keys': ['fastqc_module'],
                             'meaning': 'observed_native',
                             'precision': 'not_reported',
                             'value_domain': 'finite_number',
                             'interpretation': 'Grouped means average per-position means; grouped '
                                               'quantiles average source per-position quantiles '
                                               'with >100 observations. Not pooled quantiles or a '
                                               'per-base score histogram.',
                             'denominator': None,
                             'coordinates': 'closed 1-based native bins',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Native NaN/nonfinite -> null explicit '
                                                 'nonfinite_native; no graph recovery from HTML.',
                             'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerBaseQualityScores.java'},
 'fastqc_base_quality_p90': {'metric': 'fastqc_base_quality_p90',
                             'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                             'section_key': 'fastqc_per_base_quality',
                             'native_fields': ['90th Percentile'],
                             'units': ['phred'],
                             'axis_kinds': ['base_closed_1'],
                             'population_keys': ['fastqc_module'],
                             'meaning': 'observed_native',
                             'precision': 'not_reported',
                             'value_domain': 'finite_number',
                             'interpretation': 'Grouped means average per-position means; grouped '
                                               'quantiles average source per-position quantiles '
                                               'with >100 observations. Not pooled quantiles or a '
                                               'per-base score histogram.',
                             'denominator': None,
                             'coordinates': 'closed 1-based native bins',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Native NaN/nonfinite -> null explicit '
                                                 'nonfinite_native; no graph recovery from HTML.',
                             'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerBaseQualityScores.java'},
 'fastqc_tile_quality_deviation': {'metric': 'fastqc_tile_quality_deviation',
                                   'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                   'section_key': 'fastqc_per_tile_quality',
                                   'native_fields': ['Tile', 'Base', 'Mean'],
                                   'units': ['phred_deviation'],
                                   'axis_kinds': ['tile_base_closed_1'],
                                   'population_keys': ['fastqc_module'],
                                   'meaning': 'native_normalized',
                                   'precision': 'not_reported',
                                   'value_domain': 'finite_signed_number',
                                   'interpretation': 'Deviation from equal-tile mean, may be '
                                                     'negative. Sample first10000 then every10th '
                                                     'read; source tile parsing can omit module.',
                                   'denominator': None,
                                   'coordinates': 'closed 1-based native bins',
                                   'uncertainty': 'not_reported',
                                   'missing_behavior': 'Preserve native token and explicit state; '
                                                       'absent row is not numerical zero. Partial '
                                                       'populations retain partial counts; no '
                                                       'whole-population inference.',
                                   'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerTileQualityScores.java'},
 'fastqc_sequence_quality_count': {'metric': 'fastqc_sequence_quality_count',
                                   'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                   'section_key': 'fastqc_per_sequence_quality',
                                   'native_fields': ['Quality', 'Count'],
                                   'units': ['reads'],
                                   'axis_kinds': ['quality_score'],
                                   'population_keys': ['fastqc_module'],
                                   'meaning': 'observed_count',
                                   'precision': 'exact_for_retained_population',
                                   'value_domain': 'nonnegative_integer',
                                   'interpretation': 'Histogram of integer-truncated per-read mean '
                                                     'quality, not per-base qualities or usable '
                                                     'Q30 numerator.',
                                   'denominator': None,
                                   'coordinates': 'not_applicable',
                                   'uncertainty': 'not_reported',
                                   'missing_behavior': 'Preserve native token and explicit state; '
                                                       'absent row is not numerical zero. Partial '
                                                       'populations retain partial counts; no '
                                                       'whole-population inference.',
                                   'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerSequenceQualityScores.java'},
 'fastqc_base_content_percent': {'metric': 'fastqc_base_content_percent',
                                 'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                 'section_key': 'fastqc_per_base_content',
                                 'native_fields': ['Base', 'G', 'A', 'T', 'C'],
                                 'units': ['percent'],
                                 'axis_kinds': ['base_closed_1'],
                                 'population_keys': ['fastqc_module'],
                                 'meaning': 'native_normalized',
                                 'precision': 'not_reported',
                                 'value_domain': 'finite_number',
                                 'interpretation': 'Native percentages for each base/position '
                                                   'group. Axis label preserves G/A/T/C; do not '
                                                   'reconstruct counts or pooled weighted means.',
                                 'denominator': 'native ACGT count per position; absent from table',
                                 'coordinates': 'closed 1-based native bins',
                                 'uncertainty': 'not_reported',
                                 'missing_behavior': 'Preserve native token and explicit state; '
                                                     'absent row is not numerical zero. Partial '
                                                     'populations retain partial counts; no '
                                                     'whole-population inference.',
                                 'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerBaseSequenceContent.java'},
 'fastqc_n_percent': {'metric': 'fastqc_n_percent',
                      'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                      'section_key': 'fastqc_per_base_n',
                      'native_fields': ['Base', 'N-Count'],
                      'units': ['percent'],
                      'axis_kinds': ['base_closed_1'],
                      'population_keys': ['fastqc_module'],
                      'meaning': 'native_normalized',
                      'precision': 'not_reported',
                      'value_domain': 'finite_number',
                      'interpretation': 'N-Count column is percent, not count.',
                      'denominator': 'native N + non-N at position',
                      'coordinates': 'closed 1-based native bins',
                      'uncertainty': 'not_reported',
                      'missing_behavior': 'Preserve native token and explicit state; absent row is '
                                          'not numerical zero. Partial populations retain partial '
                                          'counts; no whole-population inference.',
                      'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/NContent.java'},
 'fastqc_sequence_gc_smoothed_count': {'metric': 'fastqc_sequence_gc_smoothed_count',
                                       'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                       'section_key': 'fastqc_per_sequence_gc',
                                       'native_fields': ['GC Content', 'Count'],
                                       'units': ['native_count'],
                                       'axis_kinds': ['native_label'],
                                       'population_keys': ['fastqc_module'],
                                       'meaning': 'native_estimate',
                                       'precision': 'native_estimator',
                                       'value_domain': 'nonnegative_number',
                                       'interpretation': 'Smoothed fractional histogram. Source '
                                                         'truncates long sequences to '
                                                         'hundred/thousand boundaries. Not integer '
                                                         'read-bucket counts.',
                                       'denominator': None,
                                       'coordinates': 'not_applicable',
                                       'uncertainty': 'not_reported',
                                       'missing_behavior': 'Preserve native token and explicit '
                                                           'state; absent row is not numerical '
                                                           'zero. Partial populations retain '
                                                           'partial counts; no whole-population '
                                                           'inference.',
                                       'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/PerSequenceGCContent.java'},
 'fastqc_length_bin_count': {'metric': 'fastqc_length_bin_count',
                             'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                             'section_key': 'fastqc_length_distribution',
                             'native_fields': ['Length', 'Count'],
                             'units': ['reads'],
                             'axis_kinds': ['length_closed'],
                             'population_keys': ['fastqc_module'],
                             'meaning': 'observed_count',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Grouped closed length bins; cannot derive exact '
                                               'bases/mean from nonsingleton bins.',
                             'denominator': None,
                             'coordinates': 'closed native axis bins; BAM positions separately '
                                            'zero-based',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Preserve native token and explicit state; absent '
                                                 'row is not numerical zero. Partial populations '
                                                 'retain partial counts; no whole-population '
                                                 'inference.',
                             'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/SequenceLengthDistribution.java'},
 'fastqc_total_deduplicated_percent': {'metric': 'fastqc_total_deduplicated_percent',
                                       'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                       'section_key': 'fastqc_duplication',
                                       'native_fields': ['Total Deduplicated Percentage'],
                                       'units': ['percent'],
                                       'axis_kinds': ['none', 'duplication_bin'],
                                       'population_keys': ['fastqc_module'],
                                       'meaning': 'native_estimate',
                                       'precision': 'native_estimator',
                                       'value_domain': 'nonnegative_number',
                                       'interpretation': 'Corrected bounded-tracking estimator, '
                                                         'not observed distinct molecules; source '
                                                         'rawTotal0 fallback100 remains qualified.',
                                       'denominator': None,
                                       'coordinates': 'not_applicable',
                                       'uncertainty': 'not_reported',
                                       'missing_behavior': 'Preserve native token and explicit '
                                                           'state; absent row is not numerical '
                                                           'zero. Partial populations retain '
                                                           'partial counts; no whole-population '
                                                           'inference.',
                                       'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/DuplicationLevel.java'},
 'fastqc_duplication_bin_percent': {'metric': 'fastqc_duplication_bin_percent',
                                    'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                                    'section_key': 'fastqc_duplication',
                                    'native_fields': ['Duplication Level', 'Percentage of total'],
                                    'units': ['percent'],
                                    'axis_kinds': ['none', 'duplication_bin'],
                                    'population_keys': ['fastqc_module'],
                                    'meaning': 'native_estimate',
                                    'precision': 'native_estimator',
                                    'value_domain': 'nonnegative_number',
                                    'interpretation': 'Corrected bounded-tracking estimator, not '
                                                      'observed distinct molecules; source '
                                                      'rawTotal0 fallback100 remains qualified.',
                                    'denominator': None,
                                    'coordinates': 'not_applicable',
                                    'uncertainty': 'not_reported',
                                    'missing_behavior': 'Preserve native token and explicit state; '
                                                        'absent row is not numerical zero. Partial '
                                                        'populations retain partial counts; no '
                                                        'whole-population inference.',
                                    'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/DuplicationLevel.java'},
 'fastqc_overrepresented_count': {'metric': 'fastqc_overrepresented_count',
                                  'formats': ['fastqc_data_0_12_1',
                                              'fastqc_zip_0_12_1',
                                              'fastqc_html_0_12_1'],
                                  'section_key': 'fastqc_overrepresented',
                                  'native_fields': ['Sequence', 'Count'],
                                  'units': ['reads'],
                                  'axis_kinds': ['sequence'],
                                  'population_keys': ['fastqc_module'],
                                  'meaning': 'observed_count',
                                  'precision': 'exact_for_retained_population',
                                  'value_domain': 'nonnegative_integer',
                                  'interpretation': 'Count of tracked keys, normally first50bp; '
                                                    'first100000 distinct keys tracked. Preserve '
                                                    'native Possible Source label as a suggestion.',
                                  'denominator': None,
                                  'coordinates': 'not_applicable',
                                  'uncertainty': 'not_reported',
                                  'missing_behavior': 'Preserve native token and explicit state; '
                                                      'absent row is not numerical zero. Partial '
                                                      'populations retain partial counts; no '
                                                      'whole-population inference.',
                                  'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/OverRepresentedSeqs.java'},
 'fastqc_overrepresented_percent': {'metric': 'fastqc_overrepresented_percent',
                                    'formats': ['fastqc_data_0_12_1',
                                                'fastqc_zip_0_12_1',
                                                'fastqc_html_0_12_1'],
                                    'section_key': 'fastqc_overrepresented',
                                    'native_fields': ['Sequence', 'Percentage'],
                                    'units': ['percent'],
                                    'axis_kinds': ['sequence'],
                                    'population_keys': ['fastqc_module'],
                                    'meaning': 'native_normalized',
                                    'precision': 'not_reported',
                                    'value_domain': 'nonnegative_number',
                                    'interpretation': 'Reported tracked-key percentage; empty '
                                                      'complete table means no reported rows, not '
                                                      'no contamination.',
                                    'denominator': 'native total sequence count',
                                    'coordinates': 'not_applicable',
                                    'uncertainty': 'not_reported',
                                    'missing_behavior': 'Preserve native token and explicit state; '
                                                        'absent row is not numerical zero. Partial '
                                                        'populations retain partial counts; no '
                                                        'whole-population inference.',
                                    'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/OverRepresentedSeqs.java'},
 'fastqc_adapter_percent': {'metric': 'fastqc_adapter_percent',
                            'formats': ['fastqc_data_0_12_1', 'fastqc_zip_0_12_1'],
                            'section_key': 'fastqc_adapter_content',
                            'native_fields': ['Position', 'native adapter-name column'],
                            'units': ['percent'],
                            'axis_kinds': ['base_closed_1'],
                            'population_keys': ['fastqc_module'],
                            'meaning': 'native_normalized',
                            'precision': 'not_reported',
                            'value_domain': 'nonnegative_number',
                            'interpretation': 'Cumulative exact adapter match detection normalized '
                                              'by total reads then grouped position average; label '
                                              'is exact native adapter name. Short reads can omit '
                                              'table.',
                            'denominator': 'native total read count',
                            'coordinates': 'closed 1-based native bins',
                            'uncertainty': 'not_reported',
                            'missing_behavior': 'Preserve native token and explicit state; absent '
                                                'row is not numerical zero. Partial populations '
                                                'retain partial counts; no whole-population '
                                                'inference.',
                            'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/AdapterContent.java'},
 'fastqc_kmer_scaled_count': {'metric': 'fastqc_kmer_scaled_count',
                              'formats': ['fastqc_data_0_12_1',
                                          'fastqc_zip_0_12_1',
                                          'fastqc_html_0_12_1'],
                              'section_key': 'fastqc_kmer_content',
                              'native_fields': ['Sequence', 'Count'],
                              'units': ['scaled_native_count'],
                              'axis_kinds': ['sequence'],
                              'population_keys': ['fastqc_module'],
                              'meaning': 'native_estimate',
                              'precision': 'native_estimator',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Source samples every50th read, prefix<=500 and '
                                                'reports count()*5; preserve this native scaling '
                                                'without extrapolating whole reads. At most20 '
                                                'reported enriched kmers.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Preserve native token and explicit state; '
                                                  'absent row is not numerical zero. Partial '
                                                  'populations retain partial counts; no '
                                                  'whole-population inference.',
                              'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/KmerContent.java'},
 'fastqc_kmer_pvalue': {'metric': 'fastqc_kmer_pvalue',
                        'formats': ['fastqc_data_0_12_1',
                                    'fastqc_zip_0_12_1',
                                    'fastqc_html_0_12_1'],
                        'section_key': 'fastqc_kmer_content',
                        'native_fields': ['Sequence', 'PValue'],
                        'units': ['dimensionless'],
                        'axis_kinds': ['sequence'],
                        'population_keys': ['fastqc_module'],
                        'meaning': 'native_estimate',
                        'precision': 'native_estimator',
                        'value_domain': 'nonnegative_number',
                        'interpretation': 'Native binomial-tail/multiple-kmer value, multiplied '
                                          'by4**k. Preserve native finite value; not annotation '
                                          'probability or a universal calibrated confidence.',
                        'denominator': None,
                        'coordinates': 'not_applicable',
                        'uncertainty': 'not_reported',
                        'missing_behavior': 'Preserve native token and explicit state; absent row '
                                            'is not numerical zero. Partial populations retain '
                                            'partial counts; no whole-population inference.',
                        'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/KmerContent.java'},
 'fastqc_kmer_obs_exp_max': {'metric': 'fastqc_kmer_obs_exp_max',
                             'formats': ['fastqc_data_0_12_1',
                                         'fastqc_zip_0_12_1',
                                         'fastqc_html_0_12_1'],
                             'section_key': 'fastqc_kmer_content',
                             'native_fields': ['Sequence', 'Obs/Exp Max', 'Max Obs/Exp Position'],
                             'units': ['ratio'],
                             'axis_kinds': ['sequence'],
                             'population_keys': ['fastqc_module'],
                             'meaning': 'native_normalized',
                             'precision': 'not_reported',
                             'value_domain': 'nonnegative_number',
                             'interpretation': 'Native observed/expected ratio, despite graph '
                                               'label mentioning log2. Preserve position token in '
                                               'label/raw table.',
                             'denominator': 'source kmer expected count model',
                             'coordinates': 'not_applicable',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Preserve native token and explicit state; absent '
                                                 'row is not numerical zero. Partial populations '
                                                 'retain partial counts; no whole-population '
                                                 'inference.',
                             'reviewed_source': 'sources/FastQC/uk/ac/babraham/FastQC/Modules/KmerContent.java'},
 'trim_processed_count': {'metric': 'trim_processed_count',
                          'formats': ['trim_galore_report_0_6_10'],
                          'section_key': 'trim_summary',
                          'native_fields': ['sequences processed in total'],
                          'units': ['reads'],
                          'axis_kinds': ['none'],
                          'population_keys': ['trim_processed'],
                          'meaning': 'observed_count',
                          'precision': 'exact_for_retained_population',
                          'value_domain': 'nonnegative_integer',
                          'interpretation': 'Input read-record loop count per mate report, '
                                            'distinct from paired validation count.',
                          'denominator': None,
                          'coordinates': 'not_applicable',
                          'uncertainty': 'not_reported',
                          'missing_behavior': 'Preserve native token and explicit state; absent '
                                              'row is not numerical zero. Partial populations '
                                              'retain partial counts; no whole-population '
                                              'inference.',
                          'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                             'trim()'},
 'trim_removed_short_count': {'metric': 'trim_removed_short_count',
                              'formats': ['trim_galore_report_0_6_10'],
                              'section_key': 'trim_summary',
                              'native_fields': ['native removed short labelled counter'],
                              'units': ['reads'],
                              'axis_kinds': ['native_label'],
                              'population_keys': ['trim_removed_short'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Preserve each exact printed counter and native '
                                                'label. Different report sections/options remain '
                                                'separate; no assumed disjointness.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Preserve native token and explicit state; '
                                                  'absent row is not numerical zero. Partial '
                                                  'populations retain partial counts; no '
                                                  'whole-population inference.',
                              'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                                 'trim()'},
 'trim_removed_short_percent': {'metric': 'trim_removed_short_percent',
                                'formats': ['trim_galore_report_0_6_10'],
                                'section_key': 'trim_summary',
                                'native_fields': ['native removed short percentage'],
                                'units': ['percent'],
                                'axis_kinds': ['native_label'],
                                'population_keys': ['trim_removed_short'],
                                'meaning': 'native_normalized',
                                'precision': 'native_rounded',
                                'value_domain': 'nonnegative_number',
                                'interpretation': 'Single-read trimming percentages use sprintf '
                                                  '%.1f; retain lexical precision and N/A.',
                                'denominator': 'native sequences processed in this report',
                                'coordinates': 'not_applicable',
                                'uncertainty': 'not_reported',
                                'missing_behavior': 'Preserve native token and explicit state; '
                                                    'absent row is not numerical zero. Partial '
                                                    'populations retain partial counts; no '
                                                    'whole-population inference.',
                                'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                                   'trim()'},
 'trim_removed_n_count': {'metric': 'trim_removed_n_count',
                          'formats': ['trim_galore_report_0_6_10'],
                          'section_key': 'trim_summary',
                          'native_fields': ['native removed n labelled counter'],
                          'units': ['reads'],
                          'axis_kinds': ['native_label'],
                          'population_keys': ['trim_removed_n'],
                          'meaning': 'observed_count',
                          'precision': 'exact_for_retained_population',
                          'value_domain': 'nonnegative_integer',
                          'interpretation': 'Preserve each exact printed counter and native label. '
                                            'Different report sections/options remain separate; no '
                                            'assumed disjointness.',
                          'denominator': None,
                          'coordinates': 'not_applicable',
                          'uncertainty': 'not_reported',
                          'missing_behavior': 'Preserve native token and explicit state; absent '
                                              'row is not numerical zero. Partial populations '
                                              'retain partial counts; no whole-population '
                                              'inference.',
                          'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                             'trim()'},
 'trim_removed_n_percent': {'metric': 'trim_removed_n_percent',
                            'formats': ['trim_galore_report_0_6_10'],
                            'section_key': 'trim_summary',
                            'native_fields': ['native removed n percentage'],
                            'units': ['percent'],
                            'axis_kinds': ['native_label'],
                            'population_keys': ['trim_removed_n'],
                            'meaning': 'native_normalized',
                            'precision': 'native_rounded',
                            'value_domain': 'nonnegative_number',
                            'interpretation': 'Single-read trimming percentages use sprintf %.1f; '
                                              'retain lexical precision and N/A.',
                            'denominator': 'native sequences processed in this report',
                            'coordinates': 'not_applicable',
                            'uncertainty': 'not_reported',
                            'missing_behavior': 'Preserve native token and explicit state; absent '
                                                'row is not numerical zero. Partial populations '
                                                'retain partial counts; no whole-population '
                                                'inference.',
                            'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                               'trim()'},
 'trim_removed_long_count': {'metric': 'trim_removed_long_count',
                             'formats': ['trim_galore_report_0_6_10'],
                             'section_key': 'trim_summary',
                             'native_fields': ['native removed long labelled counter'],
                             'units': ['reads'],
                             'axis_kinds': ['native_label'],
                             'population_keys': ['trim_removed_long'],
                             'meaning': 'observed_count',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Preserve each exact printed counter and native '
                                               'label. Different report sections/options remain '
                                               'separate; no assumed disjointness.',
                             'denominator': None,
                             'coordinates': 'not_applicable',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Preserve native token and explicit state; absent '
                                                 'row is not numerical zero. Partial populations '
                                                 'retain partial counts; no whole-population '
                                                 'inference.',
                             'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                                'trim()'},
 'trim_removed_long_percent': {'metric': 'trim_removed_long_percent',
                               'formats': ['trim_galore_report_0_6_10'],
                               'section_key': 'trim_summary',
                               'native_fields': ['native removed long percentage'],
                               'units': ['percent'],
                               'axis_kinds': ['native_label'],
                               'population_keys': ['trim_removed_long'],
                               'meaning': 'native_normalized',
                               'precision': 'native_rounded',
                               'value_domain': 'nonnegative_number',
                               'interpretation': 'Single-read trimming percentages use sprintf '
                                                 '%.1f; retain lexical precision and N/A.',
                               'denominator': 'native sequences processed in this report',
                               'coordinates': 'not_applicable',
                               'uncertainty': 'not_reported',
                               'missing_behavior': 'Preserve native token and explicit state; '
                                                   'absent row is not numerical zero. Partial '
                                                   'populations retain partial counts; no '
                                                   'whole-population inference.',
                               'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                                  'trim()'},
 'trim_validation_pair_count': {'metric': 'trim_validation_pair_count',
                                'formats': ['trim_galore_report_0_6_10'],
                                'section_key': 'trim_pair_validation',
                                'native_fields': ['Total number of sequences analysed for the '
                                                  'sequence pair validation'],
                                'units': ['pairs'],
                                'axis_kinds': ['none'],
                                'population_keys': ['trim_pairs_in'],
                                'meaning': 'observed_count',
                                'precision': 'exact_for_retained_population',
                                'value_domain': 'nonnegative_integer',
                                'interpretation': 'Paired validation loop iterations/read pairs, '
                                                  'in second mate report, not individual reads.',
                                'denominator': None,
                                'coordinates': 'not_applicable',
                                'uncertainty': 'not_reported',
                                'missing_behavior': 'Preserve native token and explicit state; '
                                                    'absent row is not numerical zero. Partial '
                                                    'populations retain partial counts; no '
                                                    'whole-population inference.',
                                'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                                   'validate_paired_end_files()'},
 'trim_removed_pair_count': {'metric': 'trim_removed_pair_count',
                             'formats': ['trim_galore_report_0_6_10'],
                             'section_key': 'trim_pair_validation',
                             'native_fields': ['sequence_pairs_removed printed as removed because '
                                               'at least one read shorter'],
                             'units': ['pairs'],
                             'axis_kinds': ['native_label'],
                             'population_keys': ['trim_pairs_removed'],
                             'meaning': 'observed_count',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Mixed native counter: increments on length and '
                                               'N-filter branches; excludes too-long counter and '
                                               'zero-length maxn_fraction skip. Preserve native '
                                               'label and trim_pair_counter_mixed; not all pair '
                                               'removals.',
                             'denominator': None,
                             'coordinates': 'not_applicable',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Preserve native token and explicit state; absent '
                                                 'row is not numerical zero. Partial populations '
                                                 'retain partial counts; no whole-population '
                                                 'inference.',
                             'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                                'validate_paired_end_files()'},
 'trim_removed_pair_percent': {'metric': 'trim_removed_pair_percent',
                               'formats': ['trim_galore_report_0_6_10'],
                               'section_key': 'trim_pair_validation',
                               'native_fields': ['percentage of sequence_pairs_removed'],
                               'units': ['percent'],
                               'axis_kinds': ['native_label'],
                               'population_keys': ['trim_pairs_removed'],
                               'meaning': 'native_normalized',
                               'precision': 'native_rounded',
                               'value_domain': 'nonnegative_number',
                               'interpretation': 'Paired-validation percentage uses sprintf %.2f, '
                                                 'correcting193 generic one-decimal statement; '
                                                 'same mixed-counter qualification.',
                               'denominator': 'native pair-validation loop count',
                               'coordinates': 'not_applicable',
                               'uncertainty': 'not_reported',
                               'missing_behavior': 'Preserve native token and explicit state; '
                                                   'absent row is not numerical zero. Partial '
                                                   'populations retain partial counts; no '
                                                   'whole-population inference.',
                               'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                                  'validate_paired_end_files()'},
 'trim_native_option': {'metric': 'trim_native_option',
                        'formats': ['trim_galore_report_0_6_10'],
                        'section_key': 'trim_configuration',
                        'native_fields': ['native numeric option name/value'],
                        'units': ['phred', 'bases', 'fraction', 'dimensionless'],
                        'axis_kinds': ['native_label'],
                        'population_keys': [],
                        'meaning': 'native_configuration',
                        'precision': 'not_reported',
                        'value_domain': 'finite_number',
                        'interpretation': 'Source-reported configuration only: quality '
                                          'cutoff=Phred; length/overlap=bases; error-rate '
                                          'option=fraction. Never a measured sequencing error '
                                          'rate; unknown options remain raw labels/blocks.',
                        'denominator': None,
                        'coordinates': 'not_applicable',
                        'uncertainty': 'not_reported',
                        'missing_behavior': 'Preserve native token and explicit state; absent row '
                                            'is not numerical zero. Partial populations retain '
                                            'partial counts; no whole-population inference.',
                        'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                           'trim() and printed configuration'},
 'trim_adapter_detection_count': {'metric': 'trim_adapter_detection_count',
                                  'formats': ['trim_galore_report_0_6_10'],
                                  'section_key': 'trim_adapter_detection',
                                  'native_fields': ['adapter label',
                                                    'literal auto-detection count'],
                                  'units': ['native_count'],
                                  'axis_kinds': ['adapter'],
                                  'population_keys': [],
                                  'meaning': 'observed_count',
                                  'precision': 'exact_for_retained_population',
                                  'value_domain': 'nonnegative_integer',
                                  'interpretation': 'Source sampling boundary and literal count '
                                                    'retained; no whole-input extrapolation or '
                                                    'confidence.',
                                  'denominator': None,
                                  'coordinates': 'not_applicable',
                                  'uncertainty': 'not_reported',
                                  'missing_behavior': 'Preserve native token and explicit state; '
                                                      'absent row is not numerical zero. Partial '
                                                      'populations retain partial counts; no '
                                                      'whole-population inference.',
                                  'reviewed_source': 'sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b '
                                                     'autodetect_adapter_type()'},
 'fastq_pair_left_paired': {'metric': 'fastq_pair_left_paired',
                            'formats': ['fastq_pair_stderr_0_3'],
                            'section_key': 'fastq_pair_summary',
                            'native_fields': ['Left paired'],
                            'units': ['reads'],
                            'axis_kinds': ['none'],
                            'population_keys': ['fastq_pair_left_paired'],
                            'meaning': 'observed_count',
                            'precision': 'exact_for_retained_population',
                            'value_domain': 'nonnegative_integer',
                            'interpretation': 'Exact native read-record counter; not verified '
                                              'unique pair correspondence. Preserve '
                                              'inconsistent/negative/overflow diagnostics without '
                                              'clamping.',
                            'denominator': None,
                            'coordinates': 'not_applicable',
                            'uncertainty': 'not_reported',
                            'missing_behavior': 'Preserve native token and explicit state; absent '
                                                'row is not numerical zero. Partial populations '
                                                'retain partial counts; no whole-population '
                                                'inference.',
                            'reviewed_source': 'sources/fastq-pair/fastq_pair.c@4f697f0f13d3bfa7840279e9853345f8641cb59d'},
 'fastq_pair_right_paired': {'metric': 'fastq_pair_right_paired',
                             'formats': ['fastq_pair_stderr_0_3'],
                             'section_key': 'fastq_pair_summary',
                             'native_fields': ['Right paired'],
                             'units': ['reads'],
                             'axis_kinds': ['none'],
                             'population_keys': ['fastq_pair_right_paired'],
                             'meaning': 'observed_count',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Exact native read-record counter; not verified '
                                               'unique pair correspondence. Preserve '
                                               'inconsistent/negative/overflow diagnostics without '
                                               'clamping.',
                             'denominator': None,
                             'coordinates': 'not_applicable',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Preserve native token and explicit state; absent '
                                                 'row is not numerical zero. Partial populations '
                                                 'retain partial counts; no whole-population '
                                                 'inference.',
                             'reviewed_source': 'sources/fastq-pair/fastq_pair.c@4f697f0f13d3bfa7840279e9853345f8641cb59d'},
 'fastq_pair_left_single': {'metric': 'fastq_pair_left_single',
                            'formats': ['fastq_pair_stderr_0_3'],
                            'section_key': 'fastq_pair_summary',
                            'native_fields': ['Left single'],
                            'units': ['reads'],
                            'axis_kinds': ['none'],
                            'population_keys': ['fastq_pair_left_single'],
                            'meaning': 'observed_count',
                            'precision': 'exact_for_retained_population',
                            'value_domain': 'nonnegative_integer',
                            'interpretation': 'Exact native read-record counter; not verified '
                                              'unique pair correspondence. Preserve '
                                              'inconsistent/negative/overflow diagnostics without '
                                              'clamping.',
                            'denominator': None,
                            'coordinates': 'not_applicable',
                            'uncertainty': 'not_reported',
                            'missing_behavior': 'Preserve native token and explicit state; absent '
                                                'row is not numerical zero. Partial populations '
                                                'retain partial counts; no whole-population '
                                                'inference.',
                            'reviewed_source': 'sources/fastq-pair/fastq_pair.c@4f697f0f13d3bfa7840279e9853345f8641cb59d'},
 'fastq_pair_right_single': {'metric': 'fastq_pair_right_single',
                             'formats': ['fastq_pair_stderr_0_3'],
                             'section_key': 'fastq_pair_summary',
                             'native_fields': ['Right single'],
                             'units': ['reads'],
                             'axis_kinds': ['none'],
                             'population_keys': ['fastq_pair_right_single'],
                             'meaning': 'observed_count',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Exact native read-record counter; not verified '
                                               'unique pair correspondence. Preserve '
                                               'inconsistent/negative/overflow diagnostics without '
                                               'clamping.',
                             'denominator': None,
                             'coordinates': 'not_applicable',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Preserve native token and explicit state; absent '
                                                 'row is not numerical zero. Partial populations '
                                                 'retain partial counts; no whole-population '
                                                 'inference.',
                             'reviewed_source': 'sources/fastq-pair/fastq_pair.c@4f697f0f13d3bfa7840279e9853345f8641cb59d'},
 'hostile_reads_in': {'metric': 'hostile_reads_in',
                      'formats': ['hostile_json_1_1_0'],
                      'section_key': 'hostile_report',
                      'native_fields': ['reads_in'],
                      'units': ['reads'],
                      'axis_kinds': ['none'],
                      'population_keys': ['hostile_in'],
                      'meaning': 'observed_count',
                      'precision': 'exact_for_retained_population',
                      'value_domain': 'nonnegative_integer',
                      'interpretation': 'Native primary alignment-record count from samtools '
                                        '-F2304; individual read records, not pairs. Native '
                                        'removed=in-out; no true human-contamination claim.',
                      'denominator': None,
                      'coordinates': 'not_applicable',
                      'uncertainty': 'not_reported',
                      'missing_behavior': 'Preserve native token and explicit state; absent row is '
                                          'not numerical zero. Partial populations retain partial '
                                          'counts; no whole-population inference.',
                      'reviewed_source': 'sources/hostile_1.1.0/src/hostile/lib.py '
                                         'gather_stats_paired/gather_stats_single'},
 'hostile_reads_out': {'metric': 'hostile_reads_out',
                       'formats': ['hostile_json_1_1_0'],
                       'section_key': 'hostile_report',
                       'native_fields': ['reads_out'],
                       'units': ['reads'],
                       'axis_kinds': ['none'],
                       'population_keys': ['hostile_out'],
                       'meaning': 'observed_count',
                       'precision': 'exact_for_retained_population',
                       'value_domain': 'nonnegative_integer',
                       'interpretation': 'Native primary alignment-record count from samtools '
                                         '-F2304; individual read records, not pairs. Native '
                                         'removed=in-out; no true human-contamination claim.',
                       'denominator': None,
                       'coordinates': 'not_applicable',
                       'uncertainty': 'not_reported',
                       'missing_behavior': 'Preserve native token and explicit state; absent row '
                                           'is not numerical zero. Partial populations retain '
                                           'partial counts; no whole-population inference.',
                       'reviewed_source': 'sources/hostile_1.1.0/src/hostile/lib.py '
                                          'gather_stats_paired/gather_stats_single'},
 'hostile_reads_removed': {'metric': 'hostile_reads_removed',
                           'formats': ['hostile_json_1_1_0'],
                           'section_key': 'hostile_report',
                           'native_fields': ['reads_removed'],
                           'units': ['reads'],
                           'axis_kinds': ['none'],
                           'population_keys': ['hostile_removed'],
                           'meaning': 'observed_count',
                           'precision': 'exact_for_retained_population',
                           'value_domain': 'nonnegative_integer',
                           'interpretation': 'Native primary alignment-record count from samtools '
                                             '-F2304; individual read records, not pairs. Native '
                                             'removed=in-out; no true human-contamination claim.',
                           'denominator': None,
                           'coordinates': 'not_applicable',
                           'uncertainty': 'not_reported',
                           'missing_behavior': 'Preserve native token and explicit state; absent '
                                               'row is not numerical zero. Partial populations '
                                               'retain partial counts; no whole-population '
                                               'inference.',
                           'reviewed_source': 'sources/hostile_1.1.0/src/hostile/lib.py '
                                              'gather_stats_paired/gather_stats_single'},
 'hostile_removed_proportion': {'metric': 'hostile_removed_proportion',
                                'formats': ['hostile_json_1_1_0'],
                                'section_key': 'hostile_report',
                                'native_fields': ['reads_removed_proportion'],
                                'units': ['fraction'],
                                'axis_kinds': ['none'],
                                'population_keys': ['hostile_in'],
                                'meaning': 'native_normalized',
                                'precision': 'native_rounded',
                                'value_domain': 'number_0_1',
                                'interpretation': 'Native round((reads_in-reads_out)/reads_in,5), '
                                                  'with source zero-input fallback0 retained and '
                                                  'qualified. Reported native proportion differs '
                                                  'from derived undefined zero-denominator result.',
                                'denominator': 'same native row reads_in',
                                'coordinates': 'not_applicable',
                                'uncertainty': 'not_reported',
                                'missing_behavior': 'Preserve native token and explicit state; '
                                                    'absent row is not numerical zero. Partial '
                                                    'populations retain partial counts; no '
                                                    'whole-population inference.',
                                'reviewed_source': 'sources/hostile_1.1.0/src/hostile/lib.py '
                                                   'gather_stats_paired/gather_stats_single'},
 'bam_record_count': {'metric': 'bam_record_count',
                      'formats': ['sam_1_6', 'bam_1'],
                      'section_key': 'bam_summary',
                      'native_fields': ['all complete retained records'],
                      'units': ['alignment_records'],
                      'axis_kinds': ['none'],
                      'population_keys': ['bam_records'],
                      'meaning': 'observed_count',
                      'precision': 'exact_for_retained_population',
                      'value_domain': 'nonnegative_integer',
                      'interpretation': 'Counts describe the retained record population. '
                                        'Mapped-only BAM is not an original read denominator; '
                                        'secondary/supplementary records are not independent extra '
                                        'reads.',
                      'denominator': None,
                      'coordinates': 'not_applicable',
                      'uncertainty': 'not_reported',
                      'missing_behavior': 'Preserve native token and explicit state; absent row is '
                                          'not numerical zero. Partial populations retain partial '
                                          'counts; no whole-population inference.',
                      'reviewed_source': 'sources/hts-specs/SAMv1.tex mandatory fields and BAM'},
 'bam_primary_record_count': {'metric': 'bam_primary_record_count',
                              'formats': ['sam_1_6', 'bam_1'],
                              'section_key': 'bam_summary',
                              'native_fields': ['(FLAG & 0x900)==0'],
                              'units': ['alignment_records'],
                              'axis_kinds': ['none'],
                              'population_keys': ['bam_records'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Counts describe the retained record population. '
                                                'Mapped-only BAM is not an original read '
                                                'denominator; secondary/supplementary records are '
                                                'not independent extra reads.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Preserve native token and explicit state; '
                                                  'absent row is not numerical zero. Partial '
                                                  'populations retain partial counts; no '
                                                  'whole-population inference.',
                              'reviewed_source': 'sources/hts-specs/SAMv1.tex mandatory fields and '
                                                 'BAM'},
 'bam_secondary_record_count': {'metric': 'bam_secondary_record_count',
                                'formats': ['sam_1_6', 'bam_1'],
                                'section_key': 'bam_summary',
                                'native_fields': ['(FLAG & 0x100)!=0'],
                                'units': ['alignment_records'],
                                'axis_kinds': ['none'],
                                'population_keys': ['bam_records'],
                                'meaning': 'observed_count',
                                'precision': 'exact_for_retained_population',
                                'value_domain': 'nonnegative_integer',
                                'interpretation': 'Counts describe the retained record population. '
                                                  'Mapped-only BAM is not an original read '
                                                  'denominator; secondary/supplementary records '
                                                  'are not independent extra reads.',
                                'denominator': None,
                                'coordinates': 'not_applicable',
                                'uncertainty': 'not_reported',
                                'missing_behavior': 'Preserve native token and explicit state; '
                                                    'absent row is not numerical zero. Partial '
                                                    'populations retain partial counts; no '
                                                    'whole-population inference.',
                                'reviewed_source': 'sources/hts-specs/SAMv1.tex mandatory fields '
                                                   'and BAM'},
 'bam_supplementary_record_count': {'metric': 'bam_supplementary_record_count',
                                    'formats': ['sam_1_6', 'bam_1'],
                                    'section_key': 'bam_summary',
                                    'native_fields': ['(FLAG & 0x800)!=0'],
                                    'units': ['alignment_records'],
                                    'axis_kinds': ['none'],
                                    'population_keys': ['bam_records'],
                                    'meaning': 'observed_count',
                                    'precision': 'exact_for_retained_population',
                                    'value_domain': 'nonnegative_integer',
                                    'interpretation': 'Counts describe the retained record '
                                                      'population. Mapped-only BAM is not an '
                                                      'original read denominator; '
                                                      'secondary/supplementary records are not '
                                                      'independent extra reads.',
                                    'denominator': None,
                                    'coordinates': 'not_applicable',
                                    'uncertainty': 'not_reported',
                                    'missing_behavior': 'Preserve native token and explicit state; '
                                                        'absent row is not numerical zero. Partial '
                                                        'populations retain partial counts; no '
                                                        'whole-population inference.',
                                    'reviewed_source': 'sources/hts-specs/SAMv1.tex mandatory '
                                                       'fields and BAM'},
 'bam_mapped_primary_count': {'metric': 'bam_mapped_primary_count',
                              'formats': ['sam_1_6', 'bam_1'],
                              'section_key': 'bam_summary',
                              'native_fields': ['primary and (FLAG & 4)==0'],
                              'units': ['alignment_records'],
                              'axis_kinds': ['none'],
                              'population_keys': ['bam_records'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Counts describe the retained record population. '
                                                'Mapped-only BAM is not an original read '
                                                'denominator; secondary/supplementary records are '
                                                'not independent extra reads.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Preserve native token and explicit state; '
                                                  'absent row is not numerical zero. Partial '
                                                  'populations retain partial counts; no '
                                                  'whole-population inference.',
                              'reviewed_source': 'sources/hts-specs/SAMv1.tex mandatory fields and '
                                                 'BAM'},
 'bam_mapq_histogram_count': {'metric': 'bam_mapq_histogram_count',
                              'formats': ['sam_1_6', 'bam_1'],
                              'section_key': 'bam_summary',
                              'native_fields': ['MAPQ0..254', 'record count'],
                              'units': ['alignment_records'],
                              'axis_kinds': ['mapq'],
                              'population_keys': ['bam_records'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'MAPQ255 unavailable is counted separately. '
                                                'Numeric MAPQ is native alignment-model output, '
                                                'not gene-function confidence.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Preserve native token and explicit state; '
                                                  'absent row is not numerical zero. Partial '
                                                  'populations retain partial counts; no '
                                                  'whole-population inference.',
                              'reviewed_source': 'sources/hts-specs/SAMv1.tex mandatory fields'},
 'bam_mapq_unavailable_count': {'metric': 'bam_mapq_unavailable_count',
                                'formats': ['sam_1_6', 'bam_1'],
                                'section_key': 'bam_summary',
                                'native_fields': ['MAPQ==255'],
                                'units': ['alignment_records'],
                                'axis_kinds': ['none'],
                                'population_keys': ['bam_records'],
                                'meaning': 'observed_count',
                                'precision': 'exact_for_retained_population',
                                'value_domain': 'nonnegative_integer',
                                'interpretation': 'Counts describe the retained record population. '
                                                  'Mapped-only BAM is not an original read '
                                                  'denominator; secondary/supplementary records '
                                                  'are not independent extra reads.',
                                'denominator': None,
                                'coordinates': 'not_applicable',
                                'uncertainty': 'not_reported',
                                'missing_behavior': 'Preserve native token and explicit state; '
                                                    'absent row is not numerical zero. Partial '
                                                    'populations retain partial counts; no '
                                                    'whole-population inference.',
                                'reviewed_source': 'sources/hts-specs/SAMv1.tex mandatory fields '
                                                   'and BAM'}}

_COMPONENTS = {'gc_acgt_fraction': {'metric': 'gc_acgt_fraction',
                      'method': 'composition_v1',
                      'formula': '(G+C)/(A+C+G+T)',
                      'input_fields': ['fastq_symbol_count axes A,C,G,T,N,other_iupac,invalid'],
                      'units': ['fraction'],
                      'meaning': 'derived_descriptive',
                      'uncertainty': 'not_estimated',
                      'requirements': 'Complete compatible populations and finite operands; '
                                      'positive denominator for fractions.',
                      'missing_behavior': 'Null with specific typed state/requirements; preserve '
                                          'actual available operands. Do not substitute zero, '
                                          'clamp, infer missing populations or drop sibling '
                                          'components.',
                      'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                         'source/assumption corrections'},
 'n_fraction': {'metric': 'n_fraction',
                'method': 'composition_v1',
                'formula': 'N/all_bases',
                'input_fields': ['fastq_symbol_count N', 'fastq_base_count'],
                'units': ['fraction'],
                'meaning': 'derived_descriptive',
                'uncertainty': 'not_estimated',
                'requirements': 'Complete compatible populations and finite operands; positive '
                                'denominator for fractions.',
                'missing_behavior': 'Null with specific typed state/requirements; preserve actual '
                                    'available operands. Do not substitute zero, clamp, infer '
                                    'missing populations or drop sibling components.',
                'source_contract': '193 CONTRACT_001 section6 plus195 additive source/assumption '
                                   'corrections'},
 'ambiguous_fraction': {'metric': 'ambiguous_fraction',
                        'method': 'composition_v1',
                        'formula': '(N+other_IUPAC)/all_bases',
                        'input_fields': ['fastq_symbol_count N,other_iupac', 'fastq_base_count'],
                        'units': ['fraction'],
                        'meaning': 'derived_descriptive',
                        'uncertainty': 'not_estimated',
                        'requirements': 'Complete compatible populations and finite operands; '
                                        'positive denominator for fractions.',
                        'missing_behavior': 'Null with specific typed state/requirements; preserve '
                                            'actual available operands. Do not substitute zero, '
                                            'clamp, infer missing populations or drop sibling '
                                            'components.',
                        'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                           'source/assumption corrections'},
 'mean_read_length': {'metric': 'mean_read_length',
                      'method': 'composition_v1',
                      'formula': 'base_count/read_count',
                      'input_fields': ['fastq_base_count', 'fastq_read_count'],
                      'units': ['bases'],
                      'meaning': 'derived_descriptive',
                      'uncertainty': 'not_estimated',
                      'requirements': 'Complete compatible populations and finite operands; '
                                      'positive denominator for fractions.',
                      'missing_behavior': 'Null with specific typed state/requirements; preserve '
                                          'actual available operands. Do not substitute zero, '
                                          'clamp, infer missing populations or drop sibling '
                                          'components.',
                      'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                         'source/assumption corrections'},
 'mean_phred': {'metric': 'mean_phred',
                'method': 'quality_phred_v1',
                'formula': 'sum(n_Q*Q)/sum(n_Q)',
                'input_fields': ['quality_character_count + EncodingBasis or '
                                 'phred_histogram_count'],
                'units': ['phred'],
                'meaning': 'derived_descriptive',
                'uncertainty': 'not_estimated',
                'requirements': 'Complete per-character counts with exact source-bound declared '
                                'encoding assumption, or native SAM/BAM numeric Phred qualities '
                                'with missing mask. Q in0..93. Unknown/missing quality prevents '
                                'whole-population quality claims; no inference from FastQC means.',
                'missing_behavior': 'Null with specific typed state/requirements; preserve actual '
                                    'available operands. Do not substitute zero, clamp, infer '
                                    'missing populations or drop sibling components.',
                'source_contract': '193 CONTRACT_001 section6 plus195 additive source/assumption '
                                   'corrections'},
 'q_ge_threshold_fraction': {'metric': 'q_ge_threshold_fraction',
                             'method': 'quality_phred_v1',
                             'formula': 'sum(n_Q where Q>=explicit threshold)/sum(n_Q)',
                             'input_fields': ['histogram', 'quality_thresholds'],
                             'units': ['fraction'],
                             'meaning': 'derived_descriptive',
                             'uncertainty': 'not_estimated',
                             'requirements': 'Complete per-character counts with exact '
                                             'source-bound declared encoding assumption, or native '
                                             'SAM/BAM numeric Phred qualities with missing mask. Q '
                                             'in0..93. Unknown/missing quality prevents '
                                             'whole-population quality claims; no inference from '
                                             'FastQC means.',
                             'missing_behavior': 'Null with specific typed state/requirements; '
                                                 'preserve actual available operands. Do not '
                                                 'substitute zero, clamp, infer missing '
                                                 'populations or drop sibling components.',
                             'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                'source/assumption corrections'},
 'phred_implied_expected_errors': {'metric': 'phred_implied_expected_errors',
                                   'method': 'quality_phred_v1',
                                   'formula': 'sum(n_Q*10**(-Q/10))',
                                   'input_fields': ['histogram', 'EncodingBasis'],
                                   'units': ['expected_errors'],
                                   'meaning': 'phred_model_prediction',
                                   'uncertainty': 'phred_model_only',
                                   'requirements': 'Complete per-character counts with exact '
                                                   'source-bound declared encoding assumption, or '
                                                   'native SAM/BAM numeric Phred qualities with '
                                                   'missing mask. Q in0..93. Unknown/missing '
                                                   'quality prevents whole-population quality '
                                                   'claims; no inference from FastQC means.',
                                   'missing_behavior': 'Null with specific typed '
                                                       'state/requirements; preserve actual '
                                                       'available operands. Do not substitute '
                                                       'zero, clamp, infer missing populations or '
                                                       'drop sibling components.',
                                   'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                      'source/assumption corrections'},
 'phred_implied_error_fraction': {'metric': 'phred_implied_error_fraction',
                                  'method': 'quality_phred_v1',
                                  'formula': 'phred_implied_expected_errors/sum(n_Q)',
                                  'input_fields': ['histogram', 'EncodingBasis'],
                                  'units': ['fraction'],
                                  'meaning': 'phred_model_prediction',
                                  'uncertainty': 'phred_model_only',
                                  'requirements': 'Complete per-character counts with exact '
                                                  'source-bound declared encoding assumption, or '
                                                  'native SAM/BAM numeric Phred qualities with '
                                                  'missing mask. Q in0..93. Unknown/missing '
                                                  'quality prevents whole-population quality '
                                                  'claims; no inference from FastQC means.',
                                  'missing_behavior': 'Null with specific typed '
                                                      'state/requirements; preserve actual '
                                                      'available operands. Do not substitute zero, '
                                                      'clamp, infer missing populations or drop '
                                                      'sibling components.',
                                  'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                     'source/assumption corrections'},
 'read_retention_fraction': {'metric': 'read_retention_fraction',
                             'method': 'retention_v1',
                             'formula': 'after_count/before_count',
                             'input_fields': ['CalculationBinding before/after exact count refs',
                                              'LineageBasis'],
                             'units': ['fraction'],
                             'meaning': 'derived_descriptive',
                             'uncertainty': 'not_estimated',
                             'requirements': 'Complete compatible explicitly selected before/after '
                                             'populations; observed native edge or exact '
                                             'source-bound lineage assumption retained. Assumption '
                                             'never proves recipe execution. after>before '
                                             'incompatible; before0 undefined fraction.',
                             'missing_behavior': 'Null with specific typed state/requirements; '
                                                 'preserve actual available operands. Do not '
                                                 'substitute zero, clamp, infer missing '
                                                 'populations or drop sibling components.',
                             'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                'source/assumption corrections'},
 'base_retention_fraction': {'metric': 'base_retention_fraction',
                             'method': 'retention_v1',
                             'formula': 'after_count/before_count',
                             'input_fields': ['CalculationBinding before/after exact count refs',
                                              'LineageBasis'],
                             'units': ['fraction'],
                             'meaning': 'derived_descriptive',
                             'uncertainty': 'not_estimated',
                             'requirements': 'Complete compatible explicitly selected before/after '
                                             'populations; observed native edge or exact '
                                             'source-bound lineage assumption retained. Assumption '
                                             'never proves recipe execution. after>before '
                                             'incompatible; before0 undefined fraction.',
                             'missing_behavior': 'Null with specific typed state/requirements; '
                                                 'preserve actual available operands. Do not '
                                                 'substitute zero, clamp, infer missing '
                                                 'populations or drop sibling components.',
                             'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                'source/assumption corrections'},
 'pair_retention_fraction': {'metric': 'pair_retention_fraction',
                             'method': 'retention_v1',
                             'formula': 'after_count/before_count',
                             'input_fields': ['CalculationBinding before/after exact count refs',
                                              'LineageBasis'],
                             'units': ['fraction'],
                             'meaning': 'derived_descriptive',
                             'uncertainty': 'not_estimated',
                             'requirements': 'Complete compatible explicitly selected before/after '
                                             'populations; observed native edge or exact '
                                             'source-bound lineage assumption retained. Assumption '
                                             'never proves recipe execution. after>before '
                                             'incompatible; before0 undefined fraction.',
                             'missing_behavior': 'Null with specific typed state/requirements; '
                                                 'preserve actual available operands. Do not '
                                                 'substitute zero, clamp, infer missing '
                                                 'populations or drop sibling components.',
                             'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                'source/assumption corrections'},
 'removed_count': {'metric': 'removed_count',
                   'method': 'retention_v1',
                   'formula': 'before_count-after_count',
                   'input_fields': ['before/after count refs', 'LineageBasis'],
                   'units': ['reads', 'bases', 'pairs', 'alignment_records'],
                   'meaning': 'derived_descriptive',
                   'uncertainty': 'not_estimated',
                   'requirements': 'Complete compatible explicitly selected before/after '
                                   'populations; observed native edge or exact source-bound '
                                   'lineage assumption retained. Assumption never proves recipe '
                                   'execution. after>before incompatible; before0 undefined '
                                   'fraction.',
                   'missing_behavior': 'Null with specific typed state/requirements; preserve '
                                       'actual available operands. Do not substitute zero, clamp, '
                                       'infer missing populations or drop sibling components.',
                   'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                      'source/assumption corrections'},
 'removed_fraction': {'metric': 'removed_fraction',
                      'method': 'retention_v1',
                      'formula': '(before_count-after_count)/before_count',
                      'input_fields': ['before/after count refs', 'LineageBasis'],
                      'units': ['fraction'],
                      'meaning': 'derived_descriptive',
                      'uncertainty': 'not_estimated',
                      'requirements': 'Complete compatible explicitly selected before/after '
                                      'populations; observed native edge or exact source-bound '
                                      'lineage assumption retained. Assumption never proves recipe '
                                      'execution. after>before incompatible; before0 undefined '
                                      'fraction.',
                      'missing_behavior': 'Null with specific typed state/requirements; preserve '
                                          'actual available operands. Do not substitute zero, '
                                          'clamp, infer missing populations or drop sibling '
                                          'components.',
                      'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                         'source/assumption corrections'},
 'native_report_retention_fraction': {'metric': 'native_report_retention_fraction',
                                      'method': 'retention_v1',
                                      'formula': 'native_after_count/native_before_count',
                                      'input_fields': ['same-row native report before/after refs',
                                                       'LineageBasis'],
                                      'units': ['fraction'],
                                      'meaning': 'native_report_derived',
                                      'uncertainty': 'native_reporting_precision',
                                      'requirements': 'Complete compatible explicitly selected '
                                                      'before/after populations; observed native '
                                                      'edge or exact source-bound lineage '
                                                      'assumption retained. Assumption never '
                                                      'proves recipe execution. after>before '
                                                      'incompatible; before0 undefined fraction.',
                                      'missing_behavior': 'Null with specific typed '
                                                          'state/requirements; preserve actual '
                                                          'available operands. Do not substitute '
                                                          'zero, clamp, infer missing populations '
                                                          'or drop sibling components.',
                                      'source_contract': '193 CONTRACT_001 section6 plus195 '
                                                         'additive source/assumption corrections'},
 'distinct_mapped_read_fraction': {'metric': 'distinct_mapped_read_fraction',
                                   'method': 'mapping_v1',
                                   'formula': 'distinct input read segments having a mapped '
                                              'primary record / full input read count',
                                   'input_fields': ['complete input SequenceRecord[]',
                                                    'AlignmentRecord[] flags/QNAME/segment '
                                                    'identity',
                                                    'explicit read_key_rule'],
                                   'units': ['fraction'],
                                   'meaning': 'derived_descriptive',
                                   'uncertainty': 'not_estimated',
                                   'requirements': 'Requires actual unique segment joins, complete '
                                                   'input denominator and compatible selected '
                                                   'populations. Mapped-only BAM/BAI is '
                                                   'insufficient. No pair halving or native '
                                                   'filename join.',
                                   'missing_behavior': 'Null with specific typed '
                                                       'state/requirements; preserve actual '
                                                       'available operands. Do not substitute '
                                                       'zero, clamp, infer missing populations or '
                                                       'drop sibling components.',
                                   'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                      'source/assumption corrections'},
 'primary_record_fraction': {'metric': 'primary_record_fraction',
                             'method': 'mapping_v1',
                             'formula': 'bam_primary_record_count/bam_record_count',
                             'input_fields': ['same retained complete BAM/SAM population counts'],
                             'units': ['fraction'],
                             'meaning': 'derived_descriptive',
                             'uncertainty': 'not_estimated',
                             'requirements': 'Complete compatible populations and finite operands; '
                                             'positive denominator for fractions.',
                             'missing_behavior': 'Null with specific typed state/requirements; '
                                                 'preserve actual available operands. Do not '
                                                 'substitute zero, clamp, infer missing '
                                                 'populations or drop sibling components.',
                             'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                'source/assumption corrections'},
 'report_count_difference': {'metric': 'report_count_difference',
                             'method': 'report_consistency_v1',
                             'formula': 'selected report count - independently observed artifact '
                                        'count',
                             'input_fields': ['explicit report/observed measurement refs',
                                              'LineageBasis'],
                             'units': ['reads', 'bases', 'pairs', 'alignment_records'],
                             'meaning': 'derived_descriptive',
                             'uncertainty': 'not_estimated',
                             'requirements': 'Same population/unit established or explicitly '
                                             'declared as an assumption; preserve signed '
                                             'difference. Native rounded percentages never '
                                             'silently replace exact counts.',
                             'missing_behavior': 'Null with specific typed state/requirements; '
                                                 'preserve actual available operands. Do not '
                                                 'substitute zero, clamp, infer missing '
                                                 'populations or drop sibling components.',
                             'source_contract': '193 CONTRACT_001 section6 plus195 additive '
                                                'source/assumption corrections'}}

# Explicit additive003 interpretation/basis corrections; no arithmetic changes.
_METRICS['phred_histogram_count'].update({'encoding_basis_by_format': {'sam_1_6': {'basis': 'native_sam_phred',
                                          'encoding': 'phred33'},
                              'bam_1': {'basis': 'native_bam_phred',
                                        'encoding': 'bam_phred'}}})
_COMPONENTS['removed_count'].update({'meaning_by_comparison_kind': {'native_report_retention': 'native_report_derived',
                                'read_retention': 'derived_descriptive',
                                'base_retention': 'derived_descriptive',
                                'pair_retention': 'derived_descriptive'},
 'uncertainty_by_comparison_kind': {'native_report_retention': 'native_reporting_precision',
                                    'read_retention': 'not_estimated',
                                    'base_retention': 'not_estimated',
                                    'pair_retention': 'not_estimated'}})
_COMPONENTS['removed_fraction'].update({'meaning_by_comparison_kind': {'native_report_retention': 'native_report_derived',
                                'read_retention': 'derived_descriptive',
                                'base_retention': 'derived_descriptive',
                                'pair_retention': 'derived_descriptive'},
 'uncertainty_by_comparison_kind': {'native_report_retention': 'native_reporting_precision',
                                    'read_retention': 'not_estimated',
                                    'base_retention': 'not_estimated',
                                    'pair_retention': 'not_estimated'}})

METRIC_ORDER = tuple(_METRICS)
COMPONENT_ORDER = tuple(_COMPONENTS)


def metric_spec(metric: str) -> dict:
    if type(metric) is not str or metric not in _METRICS:
        raise FastqUtilsContractError('shape_invalid')
    return deepcopy(_METRICS[metric])


def component_spec(metric: str) -> dict:
    if type(metric) is not str or metric not in _COMPONENTS:
        raise FastqUtilsContractError('shape_invalid')
    return deepcopy(_COMPONENTS[metric])
