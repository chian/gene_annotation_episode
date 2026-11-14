"""Exact current native binding release; historical validators stay with their owners.

The outer source packet authenticates this authority itself. Its finite file map
has no self-hash fiction. Pillow remains recorded runtime metadata.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

_RELEASE = {
   "files" : {
      "gene_annotation_episode/__init__.py" : "b08e7be9692cc6095dcc1aef62048ed979de4c0ffe5ba610db2f2b0ffc395d5e",
      "gene_annotation_episode/domain.py" : "ede8c98584889d77485017e66c59e4885104a3956d9251d856ef6359759112d0",
      "gene_annotation_episode/episodic_workflow/__init__.py" : "34d60b899426f5a9aee9baacb1378b3cb915e9f41e4953081891d43c4e49fdc7",
      "gene_annotation_episode/episodic_workflow/root/__init__.py" : "34d60b899426f5a9aee9baacb1378b3cb915e9f41e4953081891d43c4e49fdc7",
      "gene_annotation_episode/episodic_workflow/root/library/__init__.py" : "8d30ed6c8ec6bb3cf36f9055864001ccf4c11ff002532df3fb7e1997c0822bb4",
      "gene_annotation_episode/episodic_workflow/root/library/literature_binding_interaction_calculations.py" : "c28c4a4626f1f3fd753bac2ca63d6cca92cc8f7dd3d036260eaed0bc15b2d4de",
      "gene_annotation_episode/episodic_workflow/root/library/literature_binding_interaction_inputs.py" : "5717bb27659f0f4001613fc96dc33a72d1aa7cd84f420727a5bb5f3f37008620",
      "gene_annotation_episode/episodic_workflow/root/library/literature_binding_interaction_model_declarations.py" : "e6bc10bc5254b58349da821205218bbb910e4eb5e373899815478b6dc7c3d5df",
      "gene_annotation_episode/episodic_workflow/root/library/literature_binding_interaction_render.py" : "8f721dc277d444ce051117f94c03e6e7f016f40c6f3318db49348ccf5f316b3c",
      "gene_annotation_episode/episodic_workflow/root/library/literature_binding_interaction_return_contracts.py" : "468c0528ca5311a442183fcc1102aa676497f7612ad3fc2ee729a923788a64a5",
      "gene_annotation_episode/episodic_workflow/root/library/literature_binding_interaction_validation.py" : "a682a754471a474c74f74c60dad6afe8bff2fbb44cda50d5e2d401cb9e114078",
      "gene_annotation_episode/episodic_workflow/root/library/literature_binding_reader.py" : "e117105486773280edf1dba796ab2be10c61feb6a9c0ad407ba876e2332714a1",
      "gene_annotation_episode/episodic_workflow/root/library/literature_binding_visual_inputs.py" : "8153f555699cd9b1dea63bd8ccc29869c70e127c205bdb10fd26c979b202b718",
      "gene_annotation_episode/episodic_workflow/root/library/literature_experimental_contracts.py" : "a0bd6b0de26914f65722669f0aff45e803d143e35176d47ab3f53bc60747963b",
      "gene_annotation_episode/episodic_workflow/root/library/literature_native_rate_return_schema.py" : "dfbbe1b062fe6bb096680f39ef97eaf2cd99525f59624eb66cdde9a5a0fb45b7",
      "gene_annotation_episode/episodic_workflow/root/library/literature_rate_calculations.py" : "231920fc1f20bc15d17e7303c14d36a81c68eace4dcd25f3bcbc30a54e925657",
      "gene_annotation_episode/episodic_workflow/root/library/literature_rate_reader.py" : "f92a36c6ddd72e633854f34ba13ec23d98e18a6f8936eadca6da650ebd751359",
      "gene_annotation_episode/episodic_workflow/root/library/literature_rate_return_schema.py" : "1c68e616b7996a930b07fec76c21e48ec034b41e7d8af6e2fec1cc8020e4d40c",
      "gene_annotation_episode/episodic_workflow/root/library/literature_saved_adapter_definitions.py" : "b35438a826dc4bb86a823b373dd3c3b1a6f6cc1231392cd05d5d9ab37c20a970",
      "gene_annotation_episode/episodic_workflow/root/library/literature_sheet_dependency_contracts.py" : "b4feabe3b2f9db8ecfef550b8a1be50de6e80ed9e109ce2e9ceed1a0c271267f",
      "gene_annotation_episode/episodic_workflow/root/literature_binding_interaction_storage.py" : "58a9ad51772821b9e0e4ea13282c7c382ea7c8507b905c111f4852549c5a9b8c",
      "gene_annotation_episode/episodic_workflow/root/literature_rate_storage.py" : "549a236499e1c3047058d01050ea680c00983cb1fdd1618a4dd53fb095b836c7",
      "gene_annotation_episode/episodic_workflow/root/literature_sheet_updates.py" : "68627ed066f93025508764f7f62171e730311f674bfa7b7f53e92fda70996a22",
      "gene_annotation_episode/record_serialization.py" : "445af16cfb263a0088c6f7584017d830d6ce03a797e965f6920e5fae67d8bd81"
   },
   "reader_sha256" : "5717bb27659f0f4001613fc96dc33a72d1aa7cd84f420727a5bb5f3f37008620",
   "validation_version" : "binding_interaction_saved_validation_v1",
   "version" : "root_binding_interaction_implementation_v3"
}


def retained(receipt):
    """Authenticate this complete new native release without reading source files."""
    if (type(receipt) is not dict or set(receipt) != set(_RELEASE) | {'pillow_version'}
            or type(receipt.get('files')) is not dict
            or any(type(key) is not str or type(value) is not str
                   for key, value in receipt['files'].items())
            or any(type(receipt[key]) is not str for key in _RELEASE if key != 'files')
            or type(receipt.get('pillow_version')) is not str or not receipt['pillow_version']
            or {key: receipt[key] for key in _RELEASE} != _RELEASE):
        raise ValueError('native_binding_release_mismatch')
    return deepcopy(receipt)


def verify_current_sources():
    """Check selected implementation bytes without acquiring scientific inputs."""
    project = Path(__file__).resolve().parents[3]
    for relative, expected in _RELEASE['files'].items():
        if sha256((project / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(relative)


def prospective(pillow_version):
    """Check the selected native owners before fresh source interpretation."""
    if type(pillow_version) is not str or not pillow_version:
        raise ValueError('pillow_version')
    verify_current_sources()
    # Preserve the actual imported Pillow version as metadata, not a new gate.
    return {**deepcopy(_RELEASE), 'pillow_version': pillow_version}
