"""Original own-A102 synthetic structural source operands."""

def source(store, text, *, parents=(), provider='synthetic_structure_fixture', alias=False):
    artifact = store.artifact(text)
    return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact if alias else None, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')

def cif():
    fields = ('group_PDB', 'id', 'auth_atom_id', 'auth_comp_id', 'auth_asym_id', 'auth_seq_id', 'label_alt_id', 'pdbx_PDB_ins_code', 'Cartn_x', 'Cartn_y', 'Cartn_z', 'occupancy', 'B_iso_or_equiv', 'pdbx_PDB_model_num')
    return "data_synthetic\n_entry.id 1ABC\n_exptl.method 'X-RAY DIFFRACTION'\n_pdbx_audit_revision_history.ordinal 2\n_pdbx_audit_revision_history.revision_date 2026-01-02\nloop_\n" + '\n'.join(('_atom_site.' + field for field in fields)) + '\nATOM 1 OE1 GLU A 1 . ? 0 0 0 0.5 20 1\nATOM 2 OE2 GLU A 1 . ? 0 1 0 0.5 21 1\nHETATM 3 N1 LIG B 2 . ? 3 0 0 1 12 1\n'

def xml(*, entry='1ABC', revision='2', rscc='0.8'):
    return '<wwPDB-validation-information><Entry pdbid="' + entry + '" PDB-revision-number="' + revision + '" PDB-revision-date="2026-01-02" XMLcreationDate="2026-01-03"/><ModelledSubgroup model="1" chain="A" resnum="1" icode=" " altcode=" " resname="GLU" rscc="' + rscc + '"/><ModelledSubgroup model="1" chain="B" resnum="2" icode=" " altcode=" " resname="LIG" rscc="0.9"/></wwPDB-validation-information>'

def selector(chain='A', residue='1', comp='GLU'):
    return {'auth_chain': chain, 'auth_seq_id': residue, 'comp_id': comp, 'insertion_code': '', 'alt_id': '.'}
