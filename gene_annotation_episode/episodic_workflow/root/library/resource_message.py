from copy import deepcopy

class _Message:

    def __init__(self, value):
        self.value = value

    def as_record(self):
        return deepcopy(self.value)
