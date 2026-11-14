"""Connected original/private A101 requests and typed saved returns on ten edges."""
import pytest
from .test_a101_implicit_parent_protocol import no_external_execution
from .a101_parent_directional_checks import ROUTES, genuine_host, observe, original_rows


@pytest.mark.parametrize('route', ROUTES, ids=[row[0] for row in ROUTES])
@pytest.mark.parametrize('scenario', ('request-valid', 'initial-invalid', 'prepare-error', 'return-valid', 'saved-failure', 'nonreceipt-valid'))
def test_actual_original_and_private_parent_boundary(tmp_path, route, scenario):
    with genuine_host(tmp_path, route) as (workflow, source, binding):
        with original_rows(workflow):
            before = observe(workflow, source, binding, route, scenario, original=True)
        source.feedback = None
        with original_rows(workflow):
            after = observe(workflow, source, binding, route, scenario, original=False)
        assert before == after
