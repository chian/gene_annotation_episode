"""Both axes' tools for a shared parent; scientific episodes stay independent."""
from .library.partner_qualification_tool_registry import A107ToolRegistry


class PartnerChemicalToolRegistry(A107ToolRegistry):
    COMPONENT_NATIVE_AXES = ('A107', 'A110')

    def __init__(self, *args, a110_flux_balance_bindings=(), **kwargs):
        from .a110.a110_fba_hpc import normalize
        self.a110_flux_balance_bindings = normalize(a110_flux_balance_bindings)
        super().__init__(*args, **kwargs)

    def configure_component_native_hpc(self, resources):
        super().configure_component_native_hpc(resources)
        self.configure_a103_hpc(resources)
