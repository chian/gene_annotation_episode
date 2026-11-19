"""Private A106 transport identity for repairable literature field errors."""

from copy import deepcopy


class ExperimentalContractError(ValueError):
    """A repairable field/relationship failure; never an overall evidence grade."""

    def __init__(self, code, field, *, detail=None):
        self.code, self.field = code, field
        self.detail = deepcopy(detail)
        super().__init__(f"{code}:{field}")
