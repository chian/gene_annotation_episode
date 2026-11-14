"""One explicitly selected AppService/Workspace primitive.

Custody, effect reservation, durable issue/recovery and publication belong to
the host. This component makes no choices, searches, retry loops or scientific
calculations. Prepared operands are finite JSON and reconstruct locally.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from urllib.parse import urlsplit, quote

from .acquisition import AcquisitionError, SourceSnapshot
from .api_services import event
from .bvbrc_analysis_protocol import (
    decode_rpc_response, parse_task_records, parse_workspace_records, prepare_rpc_request,
)
from .bvbrc_analysis_transport import BVBRCAnalysisClient, SERVICE as TRANSPORT_SERVICE, _url
from .bvbrc_application_definitions import prepare_application
from .bvbrc_appservice_contracts import contract_schema, download_request, validate_contract, validate_request
from .bvbrc_appservice_readers import (
    _decode_json, _object_binding, decode_task_info, decode_upload, qualify_download,
)
from .bvbrc_appservice_tool_info import (
    PREFIX, OPERATIONS, LAUNCH_OPERATIONS, RESULT_OPERATIONS, operation_catalog,
)
from .domain import ContractError, canonical


from .bvbrc_appservice_service_values import SERVICE, EXECUTION_CONTRACT, _embedded_schema, _check
from .bvbrc_appservice_preparation import AppServicePreparation
from .bvbrc_appservice_response_decoding import AppServiceResponseDecoding
from .bvbrc_appservice_publication_validation import AppServicePublicationValidation


class BVBRCAppServiceService(AppServicePreparation, AppServiceResponseDecoding, AppServicePublicationValidation):
    service = SERVICE
    request_schema = _embedded_schema("AppServiceRequest")
    selector_schema = _embedded_schema("ResultSelector")

    def __init__(self, tool_registry, configuration=None, *, client=None,
                 publication_callback=None):
        config = validate_contract("ServiceConfiguration", configuration)
        _check("timeout" not in config, "transport_timeout_configuration_not_supported")
        configured = BVBRCAnalysisClient(config["endpoints"],
            authorization_env=config.get("authorization_env"),
            authorization_origins=config.get("authorization_origins", ()))
        _check(publication_callback is None or callable(publication_callback),
               "appservice_publication_callback_invalid")
        self.tools, self.configuration = tool_registry, config
        self.client = configured if client is None else client
        self.publication_callback = publication_callback
        from .bvbrc_appservice_adapters import bind_adapters
        self.scientific_adapters = bind_adapters(config['scientific_adapters'])

    def invoke(self, prepared, *, upload_content=None):
        prepared = self._prepared(prepared)
        kind, call = prepared["native_kind"], prepared["native_operands"]["call"]
        if kind == "local_prepare":
            return None
        if kind == "rpc":
            return self.client.rpc(call["rpc_request"])
        if kind == "task_info":
            return self.client.task_info(call["task_id"], call["file"])
        if kind == "download":
            selected_range = call["byte_range"]
            _check(type(call.get("max_bytes")) is int and call["max_bytes"] > 0,
                   "bvbrc_download_byte_limit_required")
            return self.client.download(call["url"], max_bytes=call["max_bytes"],
                byte_range=None if selected_range is None else tuple(selected_range))
        binding = call["content"]
        try:
            # The asynchronous executor resolves the exact artifact on the
            # Store's owning thread, before running transport in a worker.
            # Direct synchronous callers retain the same artifact-read path.
            content = (self.tools.store.get_artifact(binding["artifact_ref"])
                       if upload_content is None else upload_content)
        except (ValueError, KeyError, OSError) as error:
            raise AcquisitionError("input_not_possessed", phase="prepare", submission_outcome="not_sent") from error
        if type(content) is not bytes or len(content) != binding["byte_count"] or hashlib.sha256(content).hexdigest() != binding["sha256"]:
            raise AcquisitionError("input_bytes_mismatch", phase="prepare", submission_outcome="not_sent")
        return self.client.upload(call["node_url"], content, filename=call["filename"])

__all__ = ["BVBRCAppServiceService", "SERVICE", "EXECUTION_CONTRACT"]
