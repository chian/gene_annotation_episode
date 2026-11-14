"""Closed, byte-pinned read transport for the original336 captured fixture.

No authority result, schema, selected action or record is replaced. Logical
paths remain original; only declared filesystem reads address preserved bytes.
"""
from contextlib import contextmanager
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path, PosixPath
import sqlite3

FIXTURE=Path(__file__).parent/'fixtures/retained_protein_reader_336'
LOGICAL=Path('/home/chia/repos/gene_annotation_episode/runs/check336_protein_structure_current_v2_workflow/tmp/test_current_v2_alignment_oper0/current-v2')
INVENTORY_SHA='1c65a52b2df2375e5e69b334443033fcb1f788d579b6ebeb9a5582ab32abafc0'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


class RetainedProteinArchive:
    def __init__(self):
        inventory=(FIXTURE/'FILE_SHA256SUMS').read_bytes()
        assert sha(inventory)==INVENTORY_SHA
        self.allowed={}
        for line in inventory.decode().splitlines():
            digest,relative=line.split('  ',1)
            path=Path(relative)
            assert not path.is_absolute() and '..' not in path.parts
            assert relative not in self.allowed
            self.allowed[relative]=digest
        assert len(self.allowed)==293
        self.directories={str(parent) for name in self.allowed for parent in Path(name).parents}
        self.transported=[]
        self.verify_unchanged()
        self.proof=json.loads(self.physical('PROTEIN_STRUCTURE_CURRENT_V2_WORKFLOW.json').read_bytes())

    def physical(self, relative):
        assert type(relative) is str and relative in self.allowed, 'undeclared archived file'
        path=FIXTURE/relative
        assert not path.is_symlink() and path.is_file()
        for parent in path.parents:
            if parent==FIXTURE.parent:break
            assert not parent.is_symlink(), 'archive symlink'
        assert sha(path.read_bytes())==self.allowed[relative], 'archived file digest mismatch'
        return path

    def relative(self, logical):
        path=Path(str(logical))
        assert path.is_absolute() and '..' not in path.parts and path.is_relative_to(LOGICAL)
        return str(path.relative_to(LOGICAL))

    def verify_unchanged(self):
        for relative in self.allowed:self.physical(relative)

    def logical_file_path(self, logical):
        archive=self
        class CapturedPath(PosixPath):
            # Child paths inherit this concrete class and its sealed archive.
            # str/path equality remains the original logical value.
            def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
                assert mode in ('r','rb'), 'read-only archive transport'
                relative=archive.relative(self)
                actual=archive.physical(relative)
                archive.transported.append(relative)
                return actual.open(mode,buffering,encoding,errors,newline)
            def stat(self, *, follow_symlinks=True):
                assert follow_symlinks is True
                return archive.physical(archive.relative(self)).stat(follow_symlinks=False)
        return CapturedPath(str(logical))

    @contextmanager
    def open_store(self, axis):
        Store=import_module('gene_annotation_episode.episodic_workflow.root.'+axis+'.state').Store
        store=Store.__new__(Store)
        store.path=self.logical_file_path(LOGICAL/'state')
        store._savepoint=0
        database=self.physical('state/state.sqlite3')
        store.db=sqlite3.connect(database.resolve().as_uri()+'?mode=ro&immutable=1',uri=True,isolation_level=None)
        store.db.row_factory=store._row
        store.db.execute('PRAGMA query_only=ON')
        store.db.create_function('library_scope_record',2,store._scope_filter_record)
        try:
            yield store
            assert store.db.total_changes==0
        finally:
            store.close()
            assert sha(database.read_bytes())==self.allowed['state/state.sqlite3']

    @contextmanager
    def control_transport(self, monkeypatch, axis):
        prefix='gene_annotation_episode.episodic_workflow.root.'+axis+'.library.retained_input_authority.'
        modules=[import_module(prefix+name) for name in
                 ('protein_structure_result_receipts','native_protein_structure_preparation')]
        descriptors={}
        def transport_for(module):
            original=module._directory
            @contextmanager
            def directory(logical, *, create=False):
                assert create is False, 'retained read cannot create directories'
                relative=self.relative(logical)
                assert relative in self.directories
                assert relative.startswith(('state/artifacts/','run/execution-results/'))
                actual=FIXTURE/relative
                assert actual.is_dir() and not actual.is_symlink()
                # Reuse the original no-follow directory traversal and regular
                # file controls at the physical read boundary.
                with original(actual,create=False) as descriptor:
                    assert descriptor not in descriptors
                    descriptors[descriptor]=relative
                    try:
                        yield descriptor
                    finally:
                        del descriptors[descriptor]
            return directory
        def declared(descriptor,name):
            assert descriptor in descriptors and type(name) is str and '/' not in name
            relative=descriptors[descriptor]+'/'+name
            self.physical(relative)
            self.transported.append(relative)
        original_read=modules[0]._read
        def read(descriptor,name):
            declared(descriptor,name)
            return original_read(descriptor,name)
        original_regular=modules[1]._regular
        @contextmanager
        def regular(descriptor,name,*,flags=os.O_RDONLY):
            assert flags==os.O_RDONLY
            declared(descriptor,name)
            with original_regular(descriptor,name,flags=flags) as file_descriptor:
                yield file_descriptor
        with monkeypatch.context() as patch:
            for module in modules:patch.setattr(module,'_directory',transport_for(module))
            patch.setattr(modules[0],'_read',read)
            patch.setattr(modules[1],'_regular',regular)
            yield
        assert descriptors=={}
