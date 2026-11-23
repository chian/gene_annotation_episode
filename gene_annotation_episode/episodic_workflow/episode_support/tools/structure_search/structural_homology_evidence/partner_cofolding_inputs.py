"""The inputs of A102's ``partner_cofolding`` (design note ``docs/plan/designs/a102_partner_cofolding.md``): the SMILES of a ligand
candidate, from the RCSB chemical-component service ``https://data.rcsb.org/rest/v1/core/chemcomp/<id>``, the entry
``pdbx_chem_comp_descriptor`` of type ``SMILES_CANONICAL`` by program ``CACTVS``. A component with no such descriptor, a status
other than 200 or a transport failure raises."""
import json
import urllib.parse
import urllib.request

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.target_model_sources import (
    TRANSPORT_TIMEOUT_SECONDS)

URL_FORM = 'https://data.rcsb.org/rest/v1/core/chemcomp/<id>'
USER_AGENT = 'Mozilla/5.0'
DESCRIPTOR_TYPE = 'SMILES_CANONICAL'
DESCRIPTOR_PROGRAM = 'CACTVS'


def chemcomp_url(component_id):
    return 'https://data.rcsb.org/rest/v1/core/chemcomp/' + urllib.parse.quote(component_id, safe='')


def chemcomp_smiles(component_id):
    """The ``SMILES_CANONICAL`` descriptor by ``CACTVS`` of the chemical component ``component_id``."""
    request = urllib.request.Request(chemcomp_url(component_id), headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=TRANSPORT_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ValueError('a102_partner_cofolding_chemcomp_status:' + str(response.status))
        body = json.loads(response.read())
    found = [row['descriptor'] for row in body['pdbx_chem_comp_descriptor']
             if row['type'] == DESCRIPTOR_TYPE and row['program'] == DESCRIPTOR_PROGRAM]
    if len(found) != 1:
        raise ValueError('a102_partner_cofolding_no_' + DESCRIPTOR_TYPE.lower() + '_by_' + DESCRIPTOR_PROGRAM.lower() + ':' + component_id)
    return found[0]


__all__ = ['chemcomp_smiles', 'chemcomp_url']
