"""Original M328 controlled comparison against explicit current A101 input ports.

The frozen source and module identity stay unchanged. This is not a historical
saved-workflow or historical dependency-environment reconstruction.
"""
import builtins
import hashlib
import importlib
import importlib.util
from types import ModuleType, SimpleNamespace


_FIXTURE_SHA256 = "3ab6b866e2a0b5c4bb7605ffbf8cad693cee56fe59b0f438b13a4b2b5566c1c7"
_AXIS = "gene_annotation_episode.episodic_workflow.root.a101"
_PORTS = {
    "blast_iteration_inputs": "_iteration",
    "blast_profile_inputs": "_profile",
    "blast_pssm_inputs": "_pssm",
    "blast_sequence_database": "_sequence",
    "blast_vdb_inputs": "_vdb",
}


def load_original_m328(path, *, comparison_owner, contracts):
    """Execute exact checked fixture bytes with eight finite relative imports."""
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != _FIXTURE_SHA256:
        raise ValueError("original_m328_fixture_bytes_changed")
    if comparison_owner.__name__ != _AXIS + '.library.native_blast_database_metadata':
        raise ValueError("original_m328_comparison_owner_mismatch")
    ports = {}
    for name, attribute in _PORTS.items():
        port = getattr(comparison_owner, attribute)
        if not isinstance(port, ModuleType) or port.__name__ != _AXIS + ".library." + name:
            raise ValueError("original_m328_dependency_owner_mismatch")
        ports[name] = port
    if (not isinstance(contracts, ModuleType)
            or contracts.__name__ != _AXIS + ".library.native_blast_database_contracts"
            or comparison_owner._contracts is not contracts):
        raise ValueError("original_m328_contract_identity_mismatch")
    ports["native_blast_database_contracts"] = contracts
    domain = importlib.import_module(_AXIS + ".domain")
    if comparison_owner.parse_sequences is not domain.parse_sequences:
        raise ValueError("original_m328_sequence_parser_identity_mismatch")
    spec = importlib.util.spec_from_file_location("gene_annotation_episode._original_m328", path)
    module = importlib.util.module_from_spec(spec)
    absolute_import = builtins.__import__

    def fixture_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0:
            return absolute_import(name, globals, locals, fromlist, level)
        if level != 1 or globals is not module.__dict__:
            raise ImportError("original_m328_unaccounted_relative_import")
        requested = tuple(fromlist)
        if name == "" and len(requested) == 1 and requested[0] in ports:
            return SimpleNamespace(**{requested[0]: ports[requested[0]]})
        if name == "domain" and requested == ("parse_sequences",):
            return domain
        if name == "blast_pssm_master_inputs" and requested == ("extract_blast_pssm_master_metadata",):
            # Preserve the original deferred import, inside query_pssm handling.
            return importlib.import_module(_AXIS + ".library.blast_pssm_master_inputs")
        raise ImportError("original_m328_unaccounted_relative_import")

    module.__dict__["__builtins__"] = {**vars(builtins), "__import__": fixture_import}
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module
