"""Local copy of the half-open region validator used by A102 tasks."""


class A101ScoringUnavailable(ValueError):
    def __init__(self, code, **detail):
        self.code, self.detail = code, detail
        super().__init__(code)


def _require(condition, code, **detail):
    if not condition:
        raise A101ScoringUnavailable(code, **detail)


def intervals(values, *, length, merge_adjacent=True):
    """Exact half-open union; adjacent display blocks are not requirements."""
    _require(type(length) is int and length > 0, 'a101_positive_length_required')
    _require(isinstance(values, (list,tuple)), 'a101_invalid_interval')
    for pair in values:
        _require(isinstance(pair, (list,tuple)) and len(pair)==2
            and all(type(x) is int for x in pair) and 0<=pair[0]<pair[1]<=length,
            'a101_invalid_interval')
    result = []
    for pair in sorted(values):
        _require(isinstance(pair, (list, tuple)) and len(pair) == 2
            and all(type(x) is int for x in pair) and 0 <= pair[0] < pair[1] <= length,
            'a101_invalid_interval')
        if result and (pair[0] <= result[-1][1] if merge_adjacent else pair[0] < result[-1][1]):
            result[-1][1] = max(result[-1][1], pair[1])
        else:
            result.append(list(pair))
    return result
