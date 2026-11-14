"""Native Cutadapt field meanings; calculations remain separate functions."""

CUTADAPT_METRICS = {'cutadapt_processed_count': {'metric': 'cutadapt_processed_count',
                              'formats': ['trim_galore_report_0_6_10'],
                              'section_key': 'cutadapt_summary',
                              'native_fields': ['Total reads/read pairs processed'],
                              'units': ['reads', 'pairs'],
                              'axis_kinds': ['none'],
                              'population_keys': ['cutadapt_input_reads', 'cutadapt_input_pairs'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Exact processed input count according to native single or '
                                                'paired mode.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Retain the native token and explicit '
                                                  'missing/malformed/partial state. Omitted is not zero; '
                                                  'preserve independent valid siblings. Do not reconstruct '
                                                  'missing counts from percentages.',
                              'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                 '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_adapter_containing_reads': {'metric': 'cutadapt_adapter_containing_reads',
                                       'formats': ['trim_galore_report_0_6_10'],
                                       'section_key': 'cutadapt_summary',
                                       'native_fields': ['Reads with adapters / Read 1 or 2 with adapter'],
                                       'units': ['reads'],
                                       'axis_kinds': ['none', 'native_label'],
                                       'population_keys': ['cutadapt_adapter_reads'],
                                       'meaning': 'observed_count',
                                       'precision': 'exact_for_retained_population',
                                       'value_domain': 'nonnegative_integer',
                                       'interpretation': 'Reads with at least one adapter, separately for '
                                                         'each explicitly reported mate.',
                                       'denominator': None,
                                       'coordinates': 'not_applicable',
                                       'uncertainty': 'not_reported',
                                       'missing_behavior': 'Retain the native token and explicit '
                                                           'missing/malformed/partial state. Omitted is not '
                                                           'zero; preserve independent valid siblings. Do '
                                                           'not reconstruct missing counts from percentages.',
                                       'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                          '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_reverse_complemented_count': {'metric': 'cutadapt_reverse_complemented_count',
                                         'formats': ['trim_galore_report_0_6_10'],
                                         'section_key': 'cutadapt_summary',
                                         'native_fields': ['Reverse-complemented'],
                                         'units': ['reads', 'pairs'],
                                         'axis_kinds': ['none'],
                                         'population_keys': ['cutadapt_reverse_complemented'],
                                         'meaning': 'observed_count',
                                         'precision': 'exact_for_retained_population',
                                         'value_domain': 'nonnegative_integer',
                                         'interpretation': 'Native selected-orientation count, distinct from '
                                                           'adapter event multiplicity.',
                                         'denominator': None,
                                         'coordinates': 'not_applicable',
                                         'uncertainty': 'not_reported',
                                         'missing_behavior': 'Retain the native token and explicit '
                                                             'missing/malformed/partial state. Omitted is '
                                                             'not zero; preserve independent valid siblings. '
                                                             'Do not reconstruct missing counts from '
                                                             'percentages.',
                                         'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                            '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_filtered_count': {'metric': 'cutadapt_filtered_count',
                             'formats': ['trim_galore_report_0_6_10'],
                             'section_key': 'cutadapt_summary',
                             'native_fields': ['Read fate breakdown: native filter label'],
                             'units': ['reads', 'pairs'],
                             'axis_kinds': ['native_label'],
                             'population_keys': ['cutadapt_filtered'],
                             'meaning': 'observed_count',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Native count for the exact named filter; omitted filters '
                                               'remain absent.',
                             'denominator': None,
                             'coordinates': 'not_applicable',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Retain the native token and explicit '
                                                 'missing/malformed/partial state. Omitted is not zero; '
                                                 'preserve independent valid siblings. Do not reconstruct '
                                                 'missing counts from percentages.',
                             'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_written_count': {'metric': 'cutadapt_written_count',
                            'formats': ['trim_galore_report_0_6_10'],
                            'section_key': 'cutadapt_summary',
                            'native_fields': ['Reads/Pairs written (passing filters)'],
                            'units': ['reads', 'pairs'],
                            'axis_kinds': ['none'],
                            'population_keys': ['cutadapt_output_reads', 'cutadapt_output_pairs'],
                            'meaning': 'observed_count',
                            'precision': 'exact_for_retained_population',
                            'value_domain': 'nonnegative_integer',
                            'interpretation': 'This Cutadapt invocation output before any later Trim Galore '
                                              'filters.',
                            'denominator': None,
                            'coordinates': 'not_applicable',
                            'uncertainty': 'not_reported',
                            'missing_behavior': 'Retain the native token and explicit '
                                                'missing/malformed/partial state. Omitted is not zero; '
                                                'preserve independent valid siblings. Do not reconstruct '
                                                'missing counts from percentages.',
                            'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                               '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_processed_bases': {'metric': 'cutadapt_processed_bases',
                              'formats': ['trim_galore_report_0_6_10'],
                              'section_key': 'cutadapt_summary',
                              'native_fields': ['Total basepairs processed / Read 1 / Read 2'],
                              'units': ['bases'],
                              'axis_kinds': ['none', 'native_label'],
                              'population_keys': ['cutadapt_input_bases', 'cutadapt_mate_input_bases'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Total input bases and explicitly printed per-mate input '
                                                'bases.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Retain the native token and explicit '
                                                  'missing/malformed/partial state. Omitted is not zero; '
                                                  'preserve independent valid siblings. Do not reconstruct '
                                                  'missing counts from percentages.',
                              'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                 '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_quality_trimmed_bases': {'metric': 'cutadapt_quality_trimmed_bases',
                                    'formats': ['trim_galore_report_0_6_10'],
                                    'section_key': 'cutadapt_summary',
                                    'native_fields': ['Quality-trimmed / Read 1 / Read 2'],
                                    'units': ['bases'],
                                    'axis_kinds': ['none', 'native_label'],
                                    'population_keys': ['cutadapt_quality_removed'],
                                    'meaning': 'observed_count',
                                    'precision': 'exact_for_retained_population',
                                    'value_domain': 'nonnegative_integer',
                                    'interpretation': 'Reported bases removed by quality trimming, '
                                                      'preserving total versus mate.',
                                    'denominator': None,
                                    'coordinates': 'not_applicable',
                                    'uncertainty': 'not_reported',
                                    'missing_behavior': 'Retain the native token and explicit '
                                                        'missing/malformed/partial state. Omitted is not '
                                                        'zero; preserve independent valid siblings. Do not '
                                                        'reconstruct missing counts from percentages.',
                                    'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                       '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_poly_a_trimmed_bases': {'metric': 'cutadapt_poly_a_trimmed_bases',
                                   'formats': ['trim_galore_report_0_6_10'],
                                   'section_key': 'cutadapt_summary',
                                   'native_fields': ['Poly-A-trimmed / Read 1 / Read 2'],
                                   'units': ['bases'],
                                   'axis_kinds': ['none', 'native_label'],
                                   'population_keys': ['cutadapt_poly_a_removed'],
                                   'meaning': 'observed_count',
                                   'precision': 'exact_for_retained_population',
                                   'value_domain': 'nonnegative_integer',
                                   'interpretation': 'Reported bases removed by poly-A trimming, preserving '
                                                     'total versus mate.',
                                   'denominator': None,
                                   'coordinates': 'not_applicable',
                                   'uncertainty': 'not_reported',
                                   'missing_behavior': 'Retain the native token and explicit '
                                                       'missing/malformed/partial state. Omitted is not '
                                                       'zero; preserve independent valid siblings. Do not '
                                                       'reconstruct missing counts from percentages.',
                                   'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                      '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_written_bases': {'metric': 'cutadapt_written_bases',
                            'formats': ['trim_galore_report_0_6_10'],
                            'section_key': 'cutadapt_summary',
                            'native_fields': ['Total written (filtered) / Read 1 / Read 2'],
                            'units': ['bases'],
                            'axis_kinds': ['none', 'native_label'],
                            'population_keys': ['cutadapt_output_bases', 'cutadapt_mate_output_bases'],
                            'meaning': 'observed_count',
                            'precision': 'exact_for_retained_population',
                            'value_domain': 'nonnegative_integer',
                            'interpretation': 'Output bases for the exact invocation and explicitly reported '
                                              'mate.',
                            'denominator': None,
                            'coordinates': 'not_applicable',
                            'uncertainty': 'not_reported',
                            'missing_behavior': 'Retain the native token and explicit '
                                                'missing/malformed/partial state. Omitted is not zero; '
                                                'preserve independent valid siblings. Do not reconstruct '
                                                'missing counts from percentages.',
                            'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                               '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_reported_percent': {'metric': 'cutadapt_reported_percent',
                               'formats': ['trim_galore_report_0_6_10'],
                               'section_key': 'cutadapt_summary',
                               'native_fields': ['Parenthesized percentage accompanying a native summary '
                                                 'count'],
                               'units': ['percent'],
                               'axis_kinds': ['native_label'],
                               'population_keys': ['cutadapt_input_reads',
                                                   'cutadapt_input_pairs',
                                                   'cutadapt_input_bases',
                                                   'cutadapt_adapter_reads',
                                                   'cutadapt_filtered',
                                                   'cutadapt_reverse_complemented',
                                                   'cutadapt_output_reads',
                                                   'cutadapt_output_pairs',
                                                   'cutadapt_quality_removed',
                                                   'cutadapt_poly_a_removed',
                                                   'cutadapt_output_bases'],
                               'meaning': 'native_normalized',
                               'precision': 'native_rounded',
                               'value_domain': 'nonnegative_number',
                               'interpretation': 'One-decimal native proportion. The exact count and native '
                                                 'row locator remain separate.',
                               'denominator': 'Native named row input reads/pairs or total input bases, as '
                                              'recorded separately in the same invocation.',
                               'coordinates': 'not_applicable',
                               'uncertainty': 'native_reporting_precision',
                               'missing_behavior': 'Retain the native token and explicit '
                                                   'missing/malformed/partial state. Omitted is not zero; '
                                                   'preserve independent valid siblings. Do not reconstruct '
                                                   'missing counts from percentages.',
                               'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                  '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_adapter_length': {'metric': 'cutadapt_adapter_length',
                             'formats': ['trim_galore_report_0_6_10'],
                             'section_key': 'cutadapt_adapter',
                             'native_fields': ['Length'],
                             'units': ['bases'],
                             'axis_kinds': ['none', 'native_label'],
                             'population_keys': ['cutadapt_adapter_events'],
                             'meaning': 'native_configuration',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Native adapter parameter; linked front and back lengths '
                                               'remain separate.',
                             'denominator': None,
                             'coordinates': 'not_applicable',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Retain the native token and explicit '
                                                 'missing/malformed/partial state. Omitted is not zero; '
                                                 'preserve independent valid siblings. Do not reconstruct '
                                                 'missing counts from percentages.',
                             'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_adapter_trimmed_count': {'metric': 'cutadapt_adapter_trimmed_count',
                                    'formats': ['trim_galore_report_0_6_10'],
                                    'section_key': 'cutadapt_adapter',
                                    'native_fields': ["Trimmed / 5' trimmed / 3' trimmed",
                                                      "times, it overlapped the 5' end of a read",
                                                      "times, it overlapped the 3' end or was within the read"],
                                    'units': ['native_count'],
                                    'axis_kinds': ['none', 'native_label'],
                                    'population_keys': ['cutadapt_adapter_events'],
                                    'meaning': 'observed_count',
                                    'precision': 'exact_for_retained_population',
                                    'value_domain': 'nonnegative_integer',
                                    'interpretation': 'Adapter match/removal events; a read can contribute '
                                                      'multiple events. Preserve the AnywhereAdapter header '
                                                      'total and its separate native endpoint counters.',
                                    'denominator': None,
                                    'coordinates': 'not_applicable',
                                    'uncertainty': 'not_reported',
                                    'missing_behavior': 'Retain the native token and explicit '
                                                        'missing/malformed/partial state. Omitted is not '
                                                        'zero; preserve independent valid siblings. Do not '
                                                        'reconstruct missing counts from percentages.',
                                    'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                       '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_adapter_reverse_complemented_count': {'metric': 'cutadapt_adapter_reverse_complemented_count',
                                                 'formats': ['trim_galore_report_0_6_10'],
                                                 'section_key': 'cutadapt_adapter',
                                                 'native_fields': ['Reverse-complemented'],
                                                 'units': ['native_count'],
                                                 'axis_kinds': ['none'],
                                                 'population_keys': ['cutadapt_adapter_events'],
                                                 'meaning': 'observed_count',
                                                 'precision': 'exact_for_retained_population',
                                                 'value_domain': 'nonnegative_integer',
                                                 'interpretation': 'Native adapter-associated '
                                                                   'reverse-complemented counter.',
                                                 'denominator': None,
                                                 'coordinates': 'not_applicable',
                                                 'uncertainty': 'not_reported',
                                                 'missing_behavior': 'Retain the native token and explicit '
                                                                     'missing/malformed/partial state. '
                                                                     'Omitted is not zero; preserve '
                                                                     'independent valid siblings. Do not '
                                                                     'reconstruct missing counts from '
                                                                     'percentages.',
                                                 'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; '
                                                                    'SHA256 '
                                                                    '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_minimum_overlap': {'metric': 'cutadapt_minimum_overlap',
                              'formats': ['trim_galore_report_0_6_10'],
                              'section_key': 'cutadapt_adapter_errors',
                              'native_fields': ['Minimum overlap'],
                              'units': ['bases'],
                              'axis_kinds': ['none', 'native_label'],
                              'population_keys': ['cutadapt_adapter_events'],
                              'meaning': 'native_configuration',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Native minimum-overlap parameter, separated by linked '
                                                'adapter end.',
                              'denominator': None,
                              'coordinates': 'not_applicable',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Retain the native token and explicit '
                                                  'missing/malformed/partial state. Omitted is not zero; '
                                                  'preserve independent valid siblings. Do not reconstruct '
                                                  'missing counts from percentages.',
                              'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                 '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_allowed_errors': {'metric': 'cutadapt_allowed_errors',
                             'formats': ['trim_galore_report_0_6_10'],
                             'section_key': 'cutadapt_adapter_errors',
                             'native_fields': ['No. of allowed errors'],
                             'units': ['native_count'],
                             'axis_kinds': ['none', 'length_closed'],
                             'population_keys': ['cutadapt_adapter_events'],
                             'meaning': 'native_configuration',
                             'precision': 'exact_for_retained_population',
                             'value_domain': 'nonnegative_integer',
                             'interpretation': 'Configured errors for the native closed length interval; no '
                                               'inferred interval for an anchored scalar.',
                             'denominator': None,
                             'coordinates': 'Native closed length interval; histogram rows join by section '
                                            'and row ordinal.',
                             'uncertainty': 'not_reported',
                             'missing_behavior': 'Retain the native token and explicit '
                                                 'missing/malformed/partial state. Omitted is not zero; '
                                                 'preserve independent valid siblings. Do not reconstruct '
                                                 'missing counts from percentages.',
                             'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_histogram_length': {'metric': 'cutadapt_histogram_length',
                               'formats': ['trim_galore_report_0_6_10'],
                               'section_key': 'cutadapt_adapter_histogram',
                               'native_fields': ['length'],
                               'units': ['bases'],
                               'axis_kinds': ['length_closed'],
                               'population_keys': ['cutadapt_adapter_events'],
                               'meaning': 'observed_count',
                               'precision': 'exact_for_retained_population',
                               'value_domain': 'nonnegative_integer',
                               'interpretation': 'Removed length, potentially including flanking bases; not '
                                                 'aligned adapter length.',
                               'denominator': None,
                               'coordinates': 'Native closed length interval; histogram rows join by section '
                                              'and row ordinal.',
                               'uncertainty': 'not_reported',
                               'missing_behavior': 'Retain the native token and explicit '
                                                   'missing/malformed/partial state. Omitted is not zero; '
                                                   'preserve independent valid siblings. Do not reconstruct '
                                                   'missing counts from percentages.',
                               'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                  '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_histogram_count': {'metric': 'cutadapt_histogram_count',
                              'formats': ['trim_galore_report_0_6_10'],
                              'section_key': 'cutadapt_adapter_histogram',
                              'native_fields': ['count'],
                              'units': ['native_count'],
                              'axis_kinds': ['length_closed'],
                              'population_keys': ['cutadapt_adapter_events'],
                              'meaning': 'observed_count',
                              'precision': 'exact_for_retained_population',
                              'value_domain': 'nonnegative_integer',
                              'interpretation': 'Adapter removal events at the exact removed length and '
                                                'native end.',
                              'denominator': None,
                              'coordinates': 'Native closed length interval; histogram rows join by section '
                                             'and row ordinal.',
                              'uncertainty': 'not_reported',
                              'missing_behavior': 'Retain the native token and explicit '
                                                  'missing/malformed/partial state. Omitted is not zero; '
                                                  'preserve independent valid siblings. Do not reconstruct '
                                                  'missing counts from percentages.',
                              'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                 '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_histogram_expected_count': {'metric': 'cutadapt_histogram_expected_count',
                                       'formats': ['trim_galore_report_0_6_10'],
                                       'section_key': 'cutadapt_adapter_histogram',
                                       'native_fields': ['expect'],
                                       'units': ['native_count'],
                                       'axis_kinds': ['length_closed'],
                                       'population_keys': ['cutadapt_adapter_events'],
                                       'meaning': 'native_estimate',
                                       'precision': 'native_estimator',
                                       'value_domain': 'nonnegative_number',
                                       'interpretation': 'Native chance-model expectation rounded to one '
                                                         'decimal; retain the reported model value.',
                                       'denominator': 'Native processed count and nucleotide chance model; '
                                                      'preserve printed expectation without substituting '
                                                      'assumptions.',
                                       'coordinates': 'Native closed length interval; histogram rows join by '
                                                      'section and row ordinal.',
                                       'uncertainty': 'native_reporting_precision',
                                       'missing_behavior': 'Retain the native token and explicit '
                                                           'missing/malformed/partial state. Omitted is not '
                                                           'zero; preserve independent valid siblings. Do '
                                                           'not reconstruct missing counts from percentages.',
                                       'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                          '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_histogram_max_errors': {'metric': 'cutadapt_histogram_max_errors',
                                   'formats': ['trim_galore_report_0_6_10'],
                                   'section_key': 'cutadapt_adapter_histogram',
                                   'native_fields': ['max.err'],
                                   'units': ['native_count'],
                                   'axis_kinds': ['length_closed'],
                                   'population_keys': ['cutadapt_adapter_events'],
                                   'meaning': 'native_configuration',
                                   'precision': 'exact_for_retained_population',
                                   'value_domain': 'nonnegative_integer',
                                   'interpretation': 'Nominal native configured error bound, distinct from '
                                                     'observed error bins.',
                                   'denominator': None,
                                   'coordinates': 'Native closed length interval; histogram rows join by '
                                                  'section and row ordinal.',
                                   'uncertainty': 'not_reported',
                                   'missing_behavior': 'Retain the native token and explicit '
                                                       'missing/malformed/partial state. Omitted is not '
                                                       'zero; preserve independent valid siblings. Do not '
                                                       'reconstruct missing counts from percentages.',
                                   'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                      '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_histogram_error_count': {'metric': 'cutadapt_histogram_error_count',
                                    'formats': ['trim_galore_report_0_6_10'],
                                    'section_key': 'cutadapt_adapter_histogram',
                                    'native_fields': ['error counts'],
                                    'units': ['native_count'],
                                    'axis_kinds': ['edit_error_count'],
                                    'population_keys': ['cutadapt_adapter_events'],
                                    'meaning': 'observed_count',
                                    'precision': 'exact_for_retained_population',
                                    'value_domain': 'nonnegative_integer',
                                    'interpretation': 'Count for each explicit error-index bin. Same '
                                                      'section/row ordinal joins it to removed length.',
                                    'denominator': None,
                                    'coordinates': 'Observed edit-error index; removed length comes from the '
                                                   'same native section/row.',
                                    'uncertainty': 'not_reported',
                                    'missing_behavior': 'Retain the native token and explicit '
                                                        'missing/malformed/partial state. Omitted is not '
                                                        'zero; preserve independent valid siblings. Do not '
                                                        'reconstruct missing counts from percentages.',
                                    'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                       '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_adjacent_base_percent': {'metric': 'cutadapt_adjacent_base_percent',
                                    'formats': ['trim_galore_report_0_6_10'],
                                    'section_key': 'cutadapt_adjacent_bases',
                                    'native_fields': ['Bases preceding removed adapters: A/C/G/T/none-other'],
                                    'units': ['percent'],
                                    'axis_kinds': ['symbol'],
                                    'population_keys': ['cutadapt_adapter_events'],
                                    'meaning': 'native_normalized',
                                    'precision': 'native_rounded',
                                    'value_domain': 'nonnegative_number',
                                    'interpretation': 'Native rounded adjacent-base percentage; text does '
                                                      'not provide base counts.',
                                    'denominator': 'Native adjacent-base observation population, whose exact '
                                                   'count is not printed.',
                                    'coordinates': 'not_applicable',
                                    'uncertainty': 'native_reporting_precision',
                                    'missing_behavior': 'Retain the native token and explicit '
                                                        'missing/malformed/partial state. Omitted is not '
                                                        'zero; preserve independent valid siblings. Do not '
                                                        'reconstruct missing counts from percentages.',
                                    'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                                       '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_poly_a_length': {'metric': 'cutadapt_poly_a_length',
                            'formats': ['trim_galore_report_0_6_10'],
                            'section_key': 'cutadapt_poly_a',
                            'native_fields': ['length'],
                            'units': ['bases'],
                            'axis_kinds': ['length_closed'],
                            'population_keys': ['cutadapt_poly_a_events'],
                            'meaning': 'observed_count',
                            'precision': 'exact_for_retained_population',
                            'value_domain': 'nonnegative_integer',
                            'interpretation': 'Removed poly-A length for the native mate-specific histogram.',
                            'denominator': None,
                            'coordinates': 'Native closed length interval; histogram rows join by section '
                                           'and row ordinal.',
                            'uncertainty': 'not_reported',
                            'missing_behavior': 'Retain the native token and explicit '
                                                'missing/malformed/partial state. Omitted is not zero; '
                                                'preserve independent valid siblings. Do not reconstruct '
                                                'missing counts from percentages.',
                            'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                               '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'},
 'cutadapt_poly_a_count': {'metric': 'cutadapt_poly_a_count',
                           'formats': ['trim_galore_report_0_6_10'],
                           'section_key': 'cutadapt_poly_a',
                           'native_fields': ['count'],
                           'units': ['reads'],
                           'axis_kinds': ['length_closed'],
                           'population_keys': ['cutadapt_poly_a_events'],
                           'meaning': 'observed_count',
                           'precision': 'exact_for_retained_population',
                           'value_domain': 'nonnegative_integer',
                           'interpretation': 'Reads at the native removed poly-A length; preserve mate '
                                             'identity.',
                           'denominator': None,
                           'coordinates': 'Native closed length interval; histogram rows join by section and '
                                          'row ordinal.',
                           'uncertainty': 'not_reported',
                           'missing_behavior': 'Retain the native token and explicit '
                                               'missing/malformed/partial state. Omitted is not zero; '
                                               'preserve independent valid siblings. Do not reconstruct '
                                               'missing counts from percentages.',
                           'reviewed_source': 'Cutadapt v4.9 src/cutadapt/report.py; SHA256 '
                                              '3e179a615338a58837461d79181da6219a76f4b711133411ca4038ee3de4af8d'}}
