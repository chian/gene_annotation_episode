"""Original public disorder schema preserves finite/nonfinite distinctions."""
from importlib import import_module
import pytest

@pytest.mark.parametrize('axis',['a101','a105','a106','a108'])
@pytest.mark.parametrize('kind,finite_value,valid',[('finite',0.5,True),('nan',None,True),('finite',None,False),('nan',0.5,False)])
def test_public_packet_native_score_kind_and_value_agree(axis,kind,finite_value,valid):
    owner=import_module('gene_annotation_episode.episodic_workflow.root.'+axis+'.library.retained_input_authority.protein_disorder_result_contracts')
    public=owner.protein_disorder_result_schema('Packet')
    claims=public['properties']['values']['properties']['context']['properties']['native_log']['properties']['occurrences']['items']['anyOf']
    threshold,=[row for row in claims if row['properties']['kind']['const']=='threshold']
    schema=threshold['properties']['values']['properties']['threshold']
    value={'token':'0.5' if kind=='finite' else 'nan','kind':kind,'finite_value':finite_value}
    if valid:assert owner._shape(value,schema)==value
    else:
        with pytest.raises(ValueError,match='protein_disorder_closed_shape_required'):owner._shape(value,schema)
