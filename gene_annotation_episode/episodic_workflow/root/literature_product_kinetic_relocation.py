"""Finite Root releases for the original product and native kinetic families.

Fresh work attests these selected files. Saved work validates its immutable
release declaration without rereading sources or rerunning calculations.
The legacy release literals and validators remain in their repository owners.
This authority's own bytes are pinned by the source packet and outer compiled
release; its file table deliberately has no impossible self-hash entry.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from gene_annotation_episode.domain import ContractError

_RELEASES = {
   "kinetic" : {
      "files" : {
         "gene_annotation_episode/domain.py" : "ede8c98584889d77485017e66c59e4885104a3956d9251d856ef6359759112d0",
         "gene_annotation_episode/episodic_workflow/root/library/literature_experimental_contracts.py" : "a0bd6b0de26914f65722669f0aff45e803d143e35176d47ab3f53bc60747963b",
         "gene_annotation_episode/episodic_workflow/root/library/literature_kinetic_calculations.py" : "34268b1cf879538f1a1883f3e83f801cd4101670d9d4693f90be48d4192d9519",
         "gene_annotation_episode/episodic_workflow/root/library/literature_kinetic_formula_declarations.py" : "8f5fa2d4da762ae88f18ad67d7bca25cee48a8c6992fa381fda99021205b98b7",
         "gene_annotation_episode/episodic_workflow/root/library/literature_kinetic_inputs.py" : "a33d77c924e1d893457cc8278ce23baffaa423e0179c56cfb6ebc46a75564ef3",
         "gene_annotation_episode/episodic_workflow/root/library/literature_kinetic_return_contracts.py" : "1ec9afabfdadaf75b677d2a336fdb00bd7fdd690a1799f07b06af97ec63ed6ba",
         "gene_annotation_episode/episodic_workflow/root/library/literature_kinetic_validation.py" : "887f80be5808388b83ce4a5c5b955b45166a21ab2b510f6d3ab60b845d754aab",
         "gene_annotation_episode/episodic_workflow/root/library/literature_native_rate_return_schema.py" : "dfbbe1b062fe6bb096680f39ef97eaf2cd99525f59624eb66cdde9a5a0fb45b7",
         "gene_annotation_episode/episodic_workflow/root/library/literature_partner_defined_units.py" : "726443739980c8b4ba0463af768e455b10ff8944e749979b768185803a99081e",
         "gene_annotation_episode/episodic_workflow/root/library/literature_partner_source_fields.py" : "bda7368f5c2bc803732b8db518b1cca8dc47ac430b08564b6d5ba6acd859cfa0",
         "gene_annotation_episode/episodic_workflow/root/library/literature_rate_native_inputs.py" : "acf98763c2881516e2bf00daf1fc860db59350c9f51671121b83d322582d036e",
         "gene_annotation_episode/episodic_workflow/root/library/literature_rate_return_schema.py" : "1c68e616b7996a930b07fec76c21e48ec034b41e7d8af6e2fec1cc8020e4d40c",
         "gene_annotation_episode/episodic_workflow/root/library/literature_rate_unit_witness_schema.py" : "394efb201310e6cac783b28fe36e5ca3f755be2b040cf36dc9c1b98a2ff564e6",
         "gene_annotation_episode/episodic_workflow/root/literature_assay_inputs.py" : "d383b8551141715191575cd35204d2a80bb1c0ad1b9f1eae8aa0c7b272ea002c",
         "gene_annotation_episode/episodic_workflow/root/literature_kinetic_storage.py" : "49f28df090c7db5c2517094d01c558729d421865ac875436be819bcfb1726368",
         "gene_annotation_episode/record_serialization.py" : "445af16cfb263a0088c6f7584017d830d6ce03a797e965f6920e5fae67d8bd81"
      },
      "validation_version" : "a105_kinetic_saved_validation_v3",
      "version" : "root_kinetic_implementation_v1"
   },
   "product_coupling" : {
      "files" : {
         "gene_annotation_episode/domain.py" : "ede8c98584889d77485017e66c59e4885104a3956d9251d856ef6359759112d0",
         "gene_annotation_episode/episodic_workflow/root/library/literature_calibration_recovery_calculations.py" : "4a33584cdb4d36963e0ca6993c1b31b37670dbd2443bb580878c61e5652671eb",
         "gene_annotation_episode/episodic_workflow/root/library/literature_calibration_recovery_return_contracts.py" : "a5fd38e970c992abc34f4fe4e87e24e2187f9910cbec1371c50f78bd475db25e",
         "gene_annotation_episode/episodic_workflow/root/library/literature_experimental_contracts.py" : "a0bd6b0de26914f65722669f0aff45e803d143e35176d47ab3f53bc60747963b",
         "gene_annotation_episode/episodic_workflow/root/library/literature_native_rate_return_schema.py" : "dfbbe1b062fe6bb096680f39ef97eaf2cd99525f59624eb66cdde9a5a0fb45b7",
         "gene_annotation_episode/episodic_workflow/root/library/literature_partner_defined_units.py" : "726443739980c8b4ba0463af768e455b10ff8944e749979b768185803a99081e",
         "gene_annotation_episode/episodic_workflow/root/library/literature_partner_source_fields.py" : "bda7368f5c2bc803732b8db518b1cca8dc47ac430b08564b6d5ba6acd859cfa0",
         "gene_annotation_episode/episodic_workflow/root/library/literature_product_coupling_calculations.py" : "883db27ec6d8088318a55519d11576cd349465eaf9d247f5794ddf9c2d92adb5",
         "gene_annotation_episode/episodic_workflow/root/library/literature_product_coupling_inputs.py" : "a71decec20f0ec1213e0e31082a3fda658e4cd9c06b9d2c82666945806762467",
         "gene_annotation_episode/episodic_workflow/root/library/literature_product_coupling_metadata.py" : "e86c6bdc42459c7ca14c7cc88fff46e443f4c4392e4dc9ba14a000ac64b9c668",
         "gene_annotation_episode/episodic_workflow/root/library/literature_product_coupling_projection.py" : "e98f0b4c075282c3db9108a0b70659fbe366a91e84c76fd276659e4259b2099a",
         "gene_annotation_episode/episodic_workflow/root/library/literature_product_coupling_prompt.py" : "e520365b878325623f86a1874ce0454dc56f8ad35679e21fb5b45d26a36a3c8a",
         "gene_annotation_episode/episodic_workflow/root/library/literature_rate_native_inputs.py" : "acf98763c2881516e2bf00daf1fc860db59350c9f51671121b83d322582d036e",
         "gene_annotation_episode/episodic_workflow/root/library/literature_rate_return_schema.py" : "1c68e616b7996a930b07fec76c21e48ec034b41e7d8af6e2fec1cc8020e4d40c",
         "gene_annotation_episode/episodic_workflow/root/library/literature_rate_unit_witness_schema.py" : "394efb201310e6cac783b28fe36e5ca3f755be2b040cf36dc9c1b98a2ff564e6",
         "gene_annotation_episode/episodic_workflow/root/literature_assay_inputs.py" : "d383b8551141715191575cd35204d2a80bb1c0ad1b9f1eae8aa0c7b272ea002c",
         "gene_annotation_episode/episodic_workflow/root/literature_measurement_validation_inputs.py" : "5ab48a73da231242607593e292fda534664a1be8d21c214e61a39fe09b802d91",
         "gene_annotation_episode/episodic_workflow/root/literature_product_coupling_storage.py" : "029a8fd73f49b4f6bcbd96877407b3ffb1d9285158b546d14ff4af9701bc3501",
         "gene_annotation_episode/record_serialization.py" : "445af16cfb263a0088c6f7584017d830d6ce03a797e965f6920e5fae67d8bd81"
      },
      "version" : "root_product_coupling_implementation_v1"
   }
}


def _release(family):
    if type(family) is not str or family not in _RELEASES:
        raise ContractError('literature_product_kinetic_relocation_family_invalid')
    return _RELEASES[family]


def retained(family, receipt):
    """Authenticate this new release only; repositories retain old validators."""
    expected = _release(family)
    if (type(receipt) is not dict or set(receipt) != set(expected)
            or type(receipt.get('files')) is not dict
            or any(type(key) is not str or type(value) is not str
                   for key, value in receipt['files'].items())
            or any(type(receipt[key]) is not str for key in expected if key != 'files')
            or receipt != expected):
        raise ContractError('literature_' + family + '_saved_dependency_mismatch')


def prospective(family):
    """Attest the finite actual Root release before materializing fresh work."""
    expected = _release(family)
    project = Path(__file__).resolve().parents[3]
    for relative, digest in expected['files'].items():
        path = project / relative
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise ContractError('literature_' + family + '_implementation_dependency_mismatch')
    return deepcopy(expected)
