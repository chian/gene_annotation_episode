"""Reopen saved specialist bindings against explicit application resources.

This module composes the existing C7 bindings; it starts no episode, model
session, transport or job. Saved descriptors identify implementations and
configuration, while executable credit projections and resources remain owned
by the caller. Unknown factories require that caller's explicit C1 factory.
"""
from __future__ import annotations
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import DurableExecutionError, canonical
from .domain import validate_schema
from .episode_bindings import EpisodeBinding, EpisodeBindingRegistry
from .episode_monitoring import ProgressProvider

def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple((_freeze(item) for item in value))
    return value

def _failure(code, reference):
    return DurableExecutionError(code, affected_refs=[reference])

def _json_object(value, reference):
    if not isinstance(value, Mapping):
        raise _failure('unavailable_binding', reference)
    try:
        return json.loads(canonical(value))
    except (ValueError, TypeError, OverflowError) as error:
        raise _failure('unavailable_binding', reference) from error

def _same_record(actual, saved, reference):
    if canonical(actual) != canonical(saved):
        raise _failure('identity_conflict', reference)
_SCIENTIFIC_IMPLEMENTATION_COMPATIBILITY = (('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', 'e4127325150c14fe1e5c3d1f46dc9d956e49be7463465c4614009ebe76cc14c8'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', '4fccf743a69a2205f6e0ef529a1cd15796ae801a92f4391f4cd69b2bb0cf0bbe'), ('e4127325150c14fe1e5c3d1f46dc9d956e49be7463465c4614009ebe76cc14c8', '4fccf743a69a2205f6e0ef529a1cd15796ae801a92f4391f4cd69b2bb0cf0bbe'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', '7ff804a471528cea44b132af27f9bff810d2410d94d8c1788875c48193c6f077'), ('e4127325150c14fe1e5c3d1f46dc9d956e49be7463465c4614009ebe76cc14c8', '7ff804a471528cea44b132af27f9bff810d2410d94d8c1788875c48193c6f077'), ('4fccf743a69a2205f6e0ef529a1cd15796ae801a92f4391f4cd69b2bb0cf0bbe', '7ff804a471528cea44b132af27f9bff810d2410d94d8c1788875c48193c6f077'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', '92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e'), ('e4127325150c14fe1e5c3d1f46dc9d956e49be7463465c4614009ebe76cc14c8', '92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e'), ('4fccf743a69a2205f6e0ef529a1cd15796ae801a92f4391f4cd69b2bb0cf0bbe', '92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e'), ('7ff804a471528cea44b132af27f9bff810d2410d94d8c1788875c48193c6f077', '92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', 'eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa'), ('e4127325150c14fe1e5c3d1f46dc9d956e49be7463465c4614009ebe76cc14c8', 'eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa'), ('4fccf743a69a2205f6e0ef529a1cd15796ae801a92f4391f4cd69b2bb0cf0bbe', 'eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa'), ('7ff804a471528cea44b132af27f9bff810d2410d94d8c1788875c48193c6f077', 'eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa'), ('92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e', 'eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', 'bb82c2521faac28af76385c13dd57ff15ef7403367f57403c89fee7259591891'), ('e4127325150c14fe1e5c3d1f46dc9d956e49be7463465c4614009ebe76cc14c8', 'bb82c2521faac28af76385c13dd57ff15ef7403367f57403c89fee7259591891'), ('4fccf743a69a2205f6e0ef529a1cd15796ae801a92f4391f4cd69b2bb0cf0bbe', 'bb82c2521faac28af76385c13dd57ff15ef7403367f57403c89fee7259591891'), ('7ff804a471528cea44b132af27f9bff810d2410d94d8c1788875c48193c6f077', 'bb82c2521faac28af76385c13dd57ff15ef7403367f57403c89fee7259591891'), ('92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e', 'bb82c2521faac28af76385c13dd57ff15ef7403367f57403c89fee7259591891'), ('eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa', 'bb82c2521faac28af76385c13dd57ff15ef7403367f57403c89fee7259591891'), ('492afd4b348ab6aa961009ed9a4f486aa7c5eb0a7d6d31d56d9e7c2a37feb4f1', '2cceeac5bdfb6e81b2bbf115d2d0d04c35c3e4551f9901faa3fcdb00f08f29ff'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', '506d9e0c5a6e7494a6c4d1d95ac2b5d13da598e039a4368d5c0db0d172556a4b'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', 'd28c34a30b59fc7f96a552faae39ef69e07d0e38c2b7d83e71a25531ebd788d1'), ('506d9e0c5a6e7494a6c4d1d95ac2b5d13da598e039a4368d5c0db0d172556a4b', 'd28c34a30b59fc7f96a552faae39ef69e07d0e38c2b7d83e71a25531ebd788d1'), ('aa8079fe81f36b7d6530e1ad32411a0d46a4eebc24efce84e515167ab1cf54df', 'd28c34a30b59fc7f96a552faae39ef69e07d0e38c2b7d83e71a25531ebd788d1'), ('2cceeac5bdfb6e81b2bbf115d2d0d04c35c3e4551f9901faa3fcdb00f08f29ff', 'd28c34a30b59fc7f96a552faae39ef69e07d0e38c2b7d83e71a25531ebd788d1'), ('d28c34a30b59fc7f96a552faae39ef69e07d0e38c2b7d83e71a25531ebd788d1', 'c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f'), ('2cceeac5bdfb6e81b2bbf115d2d0d04c35c3e4551f9901faa3fcdb00f08f29ff', 'c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f'), ('aa8079fe81f36b7d6530e1ad32411a0d46a4eebc24efce84e515167ab1cf54df', 'c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f'), ('506d9e0c5a6e7494a6c4d1d95ac2b5d13da598e039a4368d5c0db0d172556a4b', 'c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', 'c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f'), ('554a98420936bdcf9e9d0190d8c88d12bdb47347c6649af47e7a2e641890759a', 'c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f'), ('c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f', '2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000'), ('d28c34a30b59fc7f96a552faae39ef69e07d0e38c2b7d83e71a25531ebd788d1', '2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000'), ('2cceeac5bdfb6e81b2bbf115d2d0d04c35c3e4551f9901faa3fcdb00f08f29ff', '2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000'), ('aa8079fe81f36b7d6530e1ad32411a0d46a4eebc24efce84e515167ab1cf54df', '2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000'), ('506d9e0c5a6e7494a6c4d1d95ac2b5d13da598e039a4368d5c0db0d172556a4b', '2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', '2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000'), ('554a98420936bdcf9e9d0190d8c88d12bdb47347c6649af47e7a2e641890759a', '2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000'), ('2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('d28c34a30b59fc7f96a552faae39ef69e07d0e38c2b7d83e71a25531ebd788d1', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('2cceeac5bdfb6e81b2bbf115d2d0d04c35c3e4551f9901faa3fcdb00f08f29ff', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('aa8079fe81f36b7d6530e1ad32411a0d46a4eebc24efce84e515167ab1cf54df', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('506d9e0c5a6e7494a6c4d1d95ac2b5d13da598e039a4368d5c0db0d172556a4b', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('554a98420936bdcf9e9d0190d8c88d12bdb47347c6649af47e7a2e641890759a', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa', '8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020'), ('2edd4a0f75e5dfd65bb0553c73ffdf1af9364414a8ebc127e169f4a4a11fc000', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('8acf06844fc4afa798bab5c7cc3747688d1f3a6999f560ad5186d6d53f592020', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('554a98420936bdcf9e9d0190d8c88d12bdb47347c6649af47e7a2e641890759a', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('d28c34a30b59fc7f96a552faae39ef69e07d0e38c2b7d83e71a25531ebd788d1', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('2cceeac5bdfb6e81b2bbf115d2d0d04c35c3e4551f9901faa3fcdb00f08f29ff', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('aa8079fe81f36b7d6530e1ad32411a0d46a4eebc24efce84e515167ab1cf54df', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('506d9e0c5a6e7494a6c4d1d95ac2b5d13da598e039a4368d5c0db0d172556a4b', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('e7e97497946263558a1c96aa68e0fe087a479377a03350914a342e8a16769b94', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('c900c6a68b1cb72110bf98bb82f43e5230acda541440062bdbcbe6acc2562a1f', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('92bc78efe50b3f3c8eecd84cab943b57060bda311ed43e33ca81fe9c4ad78f7e', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('eccc4cfc35cf6eaddf3e1d324a89a178689bb372b2b8f92263d9d17ef9bdc1fa', 'd244ea82d5ece361c7cbc208d2a7782b0657e72d54abe829bed449707cc796de'), ('f74c77cd6e9a080313662d5a3d11114bc03ff223ebac4f3c6c34e75a13fce4f3', '440744897da3527ac75775c40b94d394e9e81d71b4308a23db57591ef052b42f'), ('440744897da3527ac75775c40b94d394e9e81d71b4308a23db57591ef052b42f', '85612b5c97264c97ba2380ec2335584a5a8261c7655e54f8f04470f750e13f87'), ('f74c77cd6e9a080313662d5a3d11114bc03ff223ebac4f3c6c34e75a13fce4f3', '85612b5c97264c97ba2380ec2335584a5a8261c7655e54f8f04470f750e13f87'), ('85612b5c97264c97ba2380ec2335584a5a8261c7655e54f8f04470f750e13f87', '83a4e46070044adea366d0809fcbabf7e2637487a46b7b52c8589398f3520934'), ('440744897da3527ac75775c40b94d394e9e81d71b4308a23db57591ef052b42f', '83a4e46070044adea366d0809fcbabf7e2637487a46b7b52c8589398f3520934'), ('f74c77cd6e9a080313662d5a3d11114bc03ff223ebac4f3c6c34e75a13fce4f3', '83a4e46070044adea366d0809fcbabf7e2637487a46b7b52c8589398f3520934'), ('83a4e46070044adea366d0809fcbabf7e2637487a46b7b52c8589398f3520934', '060fbbab5c5b846162cbde6952a4d913411e971f7b81449d516beb29a4b06630'), ('85612b5c97264c97ba2380ec2335584a5a8261c7655e54f8f04470f750e13f87', '060fbbab5c5b846162cbde6952a4d913411e971f7b81449d516beb29a4b06630'), ('440744897da3527ac75775c40b94d394e9e81d71b4308a23db57591ef052b42f', '060fbbab5c5b846162cbde6952a4d913411e971f7b81449d516beb29a4b06630'), ('f74c77cd6e9a080313662d5a3d11114bc03ff223ebac4f3c6c34e75a13fce4f3', '060fbbab5c5b846162cbde6952a4d913411e971f7b81449d516beb29a4b06630'), ('060fbbab5c5b846162cbde6952a4d913411e971f7b81449d516beb29a4b06630', '39977fe39ea61eccfba5da479cae42dd90702810ce95353e5fa981208950ccd8'), ('f74c77cd6e9a080313662d5a3d11114bc03ff223ebac4f3c6c34e75a13fce4f3', '39977fe39ea61eccfba5da479cae42dd90702810ce95353e5fa981208950ccd8'), ('440744897da3527ac75775c40b94d394e9e81d71b4308a23db57591ef052b42f', '39977fe39ea61eccfba5da479cae42dd90702810ce95353e5fa981208950ccd8'), ('cf9e98737150f9dff6a5a3371e2b3424850e4ac1ae957d916caca0271b5b5a24', '3f4a6e314d2f6376e210de699545cc9fc2e14ada0ef8550954af21aa68cf33e3'))

def scientific_binding_compatible(actual, recorded):
    """Accept exact descriptors or explicitly reviewed directed code repairs.

    This does not relabel the executing implementation or change a saved
    request. Library, callable, role and configuration identities stay exact.
    """
    try:
        actual_text, recorded_text = (canonical(actual), canonical(recorded))
        actual = json.loads(actual_text)
        recorded = json.loads(recorded_text)
    except (TypeError, ValueError, OverflowError):
        return False
    fields = {'version', 'binding_id', 'implementation_sha256', 'configuration'}
    if type(actual) is not dict or type(recorded) is not dict or set(actual) != fields or (set(recorded) != fields) or any((type(value['version']) is not str or value['version'] not in {'scientific_process_episodes_v5', 'scientific_process_episodes_v6', 'scientific_process_episodes_v7', 'scientific_process_episodes_v8', 'scientific_process_episodes_v9', 'scientific_process_episodes_v10', 'scientific_process_episode_v10'} or value['binding_id'] != 'scientific_process' or (type(value['configuration']) is not dict) or (type(value['implementation_sha256']) is not str) or (len(value['implementation_sha256']) != 64) or any((c not in '0123456789abcdef' for c in value['implementation_sha256'])) for value in (actual, recorded))):
        return False
    if actual_text == recorded_text:
        return True
    if actual['version'] != 'scientific_process_episodes_v8' or recorded['version'] != actual['version']:
        return False
    pair = (recorded['implementation_sha256'], actual['implementation_sha256'])
    if pair not in _SCIENTIFIC_IMPLEMENTATION_COMPATIBILITY:
        return False
    return canonical({k: v for k, v in actual.items() if k != 'implementation_sha256'}) == canonical({k: v for k, v in recorded.items() if k != 'implementation_sha256'})

def reopen_scientific_binding(services, *, descriptor, directory):
    """Restore the caller's pinned three-slot construction from this run only."""
    from .scientific_process.episode import ScientificProcessEpisode
    from .scientific_process_library import ScientificProcessLibrary
    from .scientific_tool_library import ScientificToolLibrary
    reference = 'scientific_process'
    if directory is None:
        raise _failure('unavailable_binding', reference)
    try:
        if descriptor.get('version') not in {'scientific_process_episodes_v5', 'scientific_process_episodes_v6', 'scientific_process_episodes_v7', 'scientific_process_episodes_v8', 'scientific_process_episodes_v9', 'scientific_process_episodes_v10', 'scientific_process_episode_v10'}:
            raise _failure('unavailable_binding', reference)
        configuration = descriptor['configuration']
        expected = {'library', 'tool_library', 'child_roles'}
        if descriptor['version'] == 'scientific_process_episodes_v6' or (descriptor['version'] in {'scientific_process_episodes_v7', 'scientific_process_episodes_v8', 'scientific_process_episodes_v9', 'scientific_process_episodes_v10', 'scientific_process_episode_v10'} and 'tool_retrieval' in configuration):
            expected.add('tool_retrieval')
        if descriptor['version'] in {'scientific_process_episodes_v8', 'scientific_process_episodes_v9', 'scientific_process_episodes_v10', 'scientific_process_episode_v10'} and 'contract_information_profile' in configuration:
            expected.add('contract_information_profile')
        if descriptor['version'] in {'scientific_process_episodes_v10', 'scientific_process_episode_v10'} and 'yield_bindings' in configuration:
            expected.add('yield_bindings')
        if set(configuration) != expected:
            raise _failure('unavailable_binding', reference)
        library = ScientificProcessLibrary(Path(directory) / 'scientific-process-library')
        _same_record(library.as_record(), configuration['library'], reference)
        tools = ScientificToolLibrary(Path(directory) / 'scientific-tool-library')
        _same_record(tools.as_record(), configuration['tool_library'], reference)
        binding = ScientificProcessEpisode(services, library=library, tool_library=tools, child_roles=configuration['child_roles'], tool_retrieval=configuration.get('tool_retrieval'), contract_information_profile=configuration.get('contract_information_profile'), yield_bindings=configuration.get('yield_bindings'))
        if not scientific_binding_compatible(binding.as_record(), descriptor):
            raise _failure('identity_conflict', reference)
        return binding
    except (OSError, TypeError, ValueError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', reference) from error

@dataclass(frozen=True)
class EpisodeComposition:
    bindings: tuple[EpisodeBinding, ...]
    progress_provider: ProgressProvider | None
    resource_capabilities: tuple[Mapping[str, Any], ...]
    role_credit_projectors: Mapping[str, Callable]
    role_credit_definitions: Mapping[str, Mapping[str, Any]]

def compose_episode_bindings(services, *, store, journal, execution_backend, descriptors, job_episodes, resource_estimator, role_credit_bindings, job_progress_provider=None, directory=None, tool_registry=None) -> EpisodeComposition:
    """Reconstruct literal saved C7 descriptors without selecting any work.

    Every operational/monitoring role needs its caller's explicit ``definition``
    and ``project`` pair. Literature continues to use the separately supplied
    scientific service. No callable, monitoring unit, operational weight or
    external-resource availability is inferred from a descriptor.

    Descriptor checks precede capability reads and progress-table creation.
    ``ProgressProvider`` is composed whenever a backend is supplied, including
    runs with no monitor role, so common typed admission can receive requested
    progress references. The host installs the returned services on its own
    application instance before using a binding.
    """
    if getattr(journal, 'store', None) is not store:
        raise _failure('identity_conflict', 'journal.store')
    if not isinstance(getattr(journal, 'run_id', None), str) or not journal.run_id:
        raise _failure('unavailable_binding', 'journal.run_id')
    if not isinstance(descriptors, (tuple, list)):
        raise _failure('unavailable_binding', 'episode_bindings')
    if job_progress_provider is not None and execution_backend is None:
        raise _failure('unavailable_binding', 'execution_backend')
    saved = [_json_object(value, 'episode_bindings') for value in descriptors]
    if not isinstance(role_credit_bindings, Mapping):
        raise _failure('unavailable_binding', 'role_credit_bindings')
    projectors, definitions = ({}, {})
    for role, binding in role_credit_bindings.items():
        if not isinstance(role, str) or not role:
            raise _failure('unavailable_binding', 'role_credit_bindings')
        if not isinstance(binding, Mapping) or set(binding) != {'definition', 'project'} or (not callable(binding['project'])):
            raise _failure('unavailable_binding', role)
        definitions[role] = _freeze(_json_object(binding['definition'], role))
        projectors[role] = binding['project']
    bindings, adapters = ([], [])
    PRIVATE_FACTORIES = {'published_evidence_assessment/evidence_search_strategy_improvement': 'gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.episode', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment': 'gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction': 'gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination': 'gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement': 'gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode', 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction': 'gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode', 'published_evidence_assessment': 'gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement': 'gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.episode', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment': 'gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction': 'gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement': 'gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction': 'gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode', 'scientific_process/published_evidence_assessment': 'gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.episode', 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination': 'gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode'}
    for descriptor in saved:
        name = descriptor.get('binding_id')
        reference = name if isinstance(name, str) and name else 'episode_bindings'
        configuration = descriptor.get('configuration')
        if not isinstance(configuration, dict):
            raise _failure('unavailable_binding', reference)
        try:
            if name == 'scientific_process':
                binding = reopen_scientific_binding(services, descriptor=descriptor, directory=directory)
            elif name in PRIVATE_FACTORIES:
                binding = import_module(PRIVATE_FACTORIES[name]).LiteratureEpisode(services, **configuration)
            else:
                raise _failure('unavailable_binding', reference)
        except (TypeError, ValueError, KeyError, AttributeError) as error:
            raise _failure('unavailable_binding', reference) from error
        if name == 'scientific_process':
            if not scientific_binding_compatible(binding.as_record(), descriptor):
                raise _failure('identity_conflict', reference)
        else:
            _same_record(binding.as_record(), descriptor, reference)
        for role in binding.roles:
            if binding.credit_kind(role) != 'scientific' and role not in projectors:
                raise _failure('unavailable_binding', role)
        bindings.append(binding)
    try:
        EpisodeBindingRegistry(bindings)
    except (TypeError, ValueError) as error:
        raise _failure('identity_conflict', 'episode_bindings') from error
    progress = ProgressProvider(store, execution_backend, run_id=journal.run_id, job_provider=job_progress_provider) if execution_backend is not None else None
    return EpisodeComposition(tuple(bindings), progress, tuple(), MappingProxyType(projectors), MappingProxyType(definitions))
__all__ = ['EpisodeComposition', 'compose_episode_bindings', 'reopen_scientific_binding']
