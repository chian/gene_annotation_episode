"""binding record for this private A105 episode."""
from __future__ import annotations
from .scientific_contracts import Path, ROLE, VERSION, deepcopy, hashlib, scientific_digest
from ..implementation_sources import scientific_source_files

from gene_annotation_episode.episodic_workflow.root.a105.runtime_assets import required_runtime_asset_fingerprints

class ScientificBindingRecord:

    def as_record(self):
        implementation = scientific_digest({**required_runtime_asset_fingerprints(include_pilot=True), **{name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in scientific_source_files().items()}})
        return {'version': VERSION, 'binding_id': ROLE, 'implementation_sha256': implementation, 'configuration': {'library': deepcopy(self._library_record), 'tool_library': deepcopy(self._tools_record), 'child_roles': list(self._child_roles), **({'tool_retrieval': deepcopy(self.tool_retrieval)} if self.tool_retrieval else {}), **({'contract_information_profile': self._contract_information_profile} if self._contract_information_profile is not None else {}), **({'yield_bindings': deepcopy(self._yield_bindings)} if self._yield_bindings is not None else {})}}
