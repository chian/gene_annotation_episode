"""Private A104 scientific binding record."""
from __future__ import annotations
from .scientific_assignment_contracts import Path, ROLE, VERSION, deepcopy, hashlib, scientific_digest

class ScientificBindingRecord:

    def as_record(self):
        from gene_annotation_episode.episodic_workflow.root import receiving_context as _context_source
        _context_sources = {name: Path(_context_source.__file__).resolve().parents[3]/name for name in ('gene_annotation_episode/__init__.py', 'gene_annotation_episode/episodic_workflow/__init__.py', 'gene_annotation_episode/episodic_workflow/root/__init__.py', 'gene_annotation_episode/episodic_workflow/root/receiving_context.py', 'gene_annotation_episode/episodic_workflow/root/providers.py', 'gene_annotation_episode/episodic_workflow/root/model_session.py', 'gene_annotation_episode/episodic_workflow/root/model_presentation.py')}
        implementation = scientific_digest({**{str(path.relative_to(Path(__file__).parent.parent)): hashlib.sha256(path.read_bytes()).hexdigest() for path in Path(__file__).parent.parent.rglob('*.py') if 'tests' not in path.parts}, **{name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in _context_sources.items()}})
        return {'version': VERSION, 'binding_id': ROLE, 'implementation_sha256': implementation, 'configuration': {'library': deepcopy(self._library_record), 'tool_library': deepcopy(self._tools_record), 'child_roles': list(self._child_roles), **({'tool_retrieval': deepcopy(self.tool_retrieval)} if self.tool_retrieval else {}), **({'contract_information_profile': self._contract_information_profile} if self._contract_information_profile is not None else {}), **({'yield_bindings': deepcopy(self._yield_bindings)} if self._yield_bindings is not None else {})}}
