
import os
if 'GENE_EPISODE_HTTP_FIXTURE_BASE' in os.environ:
    from gene_annotation_episode import tool_configuration
    from test_hmmer_api_reconstruction import fixture_tools
    _original_tools = tool_configuration.build_tools
    def _explicit_fixture_tools(store, configuration=None):
        return fixture_tools(_original_tools, store, configuration)
    tool_configuration.build_tools = _explicit_fixture_tools
