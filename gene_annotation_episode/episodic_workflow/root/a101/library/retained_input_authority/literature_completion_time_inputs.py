"""Selected source operands for preparation-specific endpoint completion times.

Models nominate meanings and source spans. This reader validates custody and
literal syntax; it makes no scientific attribution, acquisition or model call.
"""
ROLES = ('numerator', 'denominator')
LITERAL_FIELDS = ('subject', 'construct', 'preparation', 'condition', 'endpoint', 'measurement_identity')
QUALIFICATIONS = ('reported_point', 'source_qualified_approximate', 'unknown', 'conflicting')
RELATIONS = ('same', 'different', 'unknown', 'conflicting')
PAIR_RELATIONS = ('supported', 'unknown', 'conflicting')
CHANGE_STATUSES = ('described', 'partial', 'unknown', 'conflicting')
COMPARISON_FIELDS = ('endpoint_relation', 'preparation_relation', 'pair_relationship', 'other_changes_status')
COMPARISON_VALUES = (RELATIONS, RELATIONS, PAIR_RELATIONS, CHANGE_STATUSES)
