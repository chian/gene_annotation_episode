"""Model-call failure identity, separate from provider transport."""
class ModelCallError(RuntimeError):
    def __init__(self, *args, diagnostic=None):
        super().__init__(*args)
        self.diagnostic = diagnostic

