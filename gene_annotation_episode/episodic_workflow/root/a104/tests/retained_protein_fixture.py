"""Declared path transport for original336 protein controls, no authority mock."""
from contextlib import contextmanager
import json
from pathlib import Path
import tarfile

from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_fluorescence_fixture import RetainedCase, digest

FIXTURE = Path(__file__).parent / 'fixtures/protein_original336'


def unpack(directory):
    manifest = json.loads((FIXTURE / 'manifest.json').read_bytes())
    assert manifest['version'] == 'a104_original336_protein_read_fixture_v1'
    assert manifest['original_controls_rewritten'] is False
    archive = FIXTURE / manifest['archive']
    assert digest(archive.read_bytes()) == manifest['archive_sha256']
    directory = Path(directory)
    with tarfile.open(archive, 'r:gz') as stream:
        entries = stream.getmembers()
        assert len(entries) == len(manifest['files'])
        assert {row.name for row in entries} == set(manifest['files'])
        for row in entries:
            assert row.isfile() and not row.issym() and not row.islnk()
            path = Path(row.name)
            assert not path.is_absolute() and '..' not in path.parts
            raw, pin = stream.extractfile(row).read(), manifest['files'][row.name]
            assert digest(raw) == pin['sha256'] and len(raw) == pin['size_bytes']
            destination = directory / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            destination.chmod(0o444)
    proof = (FIXTURE / 'original-workflow-proof.json').read_bytes()
    assert digest(proof) == manifest['workflow_proof_sha256']
    assert digest((FIXTURE / 'original-run-receipt.json').read_bytes()) == manifest['run_receipt_sha256']
    case = ProteinRetainedCase(directory, manifest, {})
    case.workflow_proof = json.loads(proof)
    return case


class ProteinRetainedCase(RetainedCase):
    @contextmanager
    def control_transport(self, monkeypatch):
        from gene_annotation_episode.episodic_workflow.root.a104.library import protein_structure_result_receipts as module
        original_directory, original_read = module._directory, module._read
        descriptors = {}
        directories = {str(Path(relative).parent) for relative in self.allowed
            if relative.startswith('run/execution-results/')}

        @contextmanager
        def directory(logical, *, create=False):
            assert create is False, 'Historical read may not create a directory'
            logical = Path(logical)
            assert logical.is_absolute() and '..' not in logical.parts and logical.is_relative_to(self.logical_root)
            relative = str(logical.relative_to(self.logical_root))
            assert relative in directories, 'undeclared historical directory'
            actual = self.directory / relative
            assert actual.is_dir() and not actual.is_symlink()
            with original_directory(actual, create=False) as descriptor:
                assert descriptor not in descriptors
                descriptors[descriptor] = relative
                try:
                    yield descriptor
                finally:
                    del descriptors[descriptor]

        def read(descriptor, name):
            assert descriptor in descriptors and type(name) is str and '/' not in name
            relative = descriptors[descriptor] + '/' + name
            assert relative in self.allowed, 'undeclared historical control'
            actual = self.directory / relative
            assert actual.is_file() and not actual.is_symlink()
            assert digest(actual.read_bytes()) == self.allowed[relative]['sha256'], 'historical control digest mismatch'
            self.transported_reads.append(relative)
            return original_read(descriptor, name)

        with monkeypatch.context() as patch:
            patch.setattr(module, '_directory', directory)
            patch.setattr(module, '_read', read)
            yield
        assert descriptors == {}
