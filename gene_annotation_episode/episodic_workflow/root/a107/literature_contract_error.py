"""Shared transport identity for repairable literature field errors."""

from copy import deepcopy


class ExperimentalContractError(ValueError):
    """A repairable field or relationship failure in an axis-local contract."""

    def __init__(self, code, field, *, detail=None):
        self.code, self.field = code, field
        self.detail = deepcopy(detail)
        super().__init__(f"{code}:{field}")
