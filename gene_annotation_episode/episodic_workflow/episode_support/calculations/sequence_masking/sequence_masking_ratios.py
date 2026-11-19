"""Original missing/zero-denominator ratio primitive used by A104 masking calculations."""

def _ratio(numerator, denominator, missing_reason=None):
    if numerator is None or denominator is None:
        if missing_reason is None:
            raise ValueError('genomic_overlap_missing_ratio_reason')
        value, reason = (None, missing_reason)
    elif denominator == 0:
        value, reason = (None, 'zero_denominator')
    else:
        if not 0 <= numerator <= denominator:
            raise ValueError('genomic_overlap_inconsistent_ratio_population')
        value, reason = (numerator / denominator, None)
    return {'numerator': numerator, 'denominator': denominator, 'value': value, 'missing_reason': reason}
