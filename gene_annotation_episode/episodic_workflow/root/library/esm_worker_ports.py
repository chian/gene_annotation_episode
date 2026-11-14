"""Select the actual supplied ESM deployment through shared process custody."""
from gene_annotation_episode.domain import ContractError


class ESMWorkerPorts:
    def __init__(self, arguments):
        # Construction performs no validation or file I/O. The shared custodian
        # first executes its original envelope/request validation boundary.
        self.arguments = arguments

    @staticmethod
    def esm_validation_owners():
        from .esm_gene_embedding_contracts import validate_esm_worker_request
        from .esm_gene_embedding_tools import esm_worker_environment, esm_worker_implementation_files
        return validate_esm_worker_request, esm_worker_environment, esm_worker_implementation_files

    def module(self, operation):
        if operation != "esm_gene_embedding":
            raise ContractError("molecular_tool_operation_unknown")
        from .esm_gene_embedding_contracts import esm_worker_module
        return esm_worker_module(self.arguments["request"]["deployment"]["driver"])

    def recorded_module(self, operation, selected):
        # The supplied deployment owns the command. The custodian compares the
        # entire recorded vector, so a mismatched saved module remains invalid.
        return self.module(operation)
