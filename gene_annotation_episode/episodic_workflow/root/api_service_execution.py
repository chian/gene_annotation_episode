"""Selected API operations in the existing episode loop, across real services.

This module records calls and qualifies their handoffs and acquisitions. Service
implementations supply individual native operations; neither layer owns a model
loop, polling schedule, retry decision or scientific interpretation.
"""
from __future__ import annotations

from .api_service_configuration import APIServiceConfiguration
from .api_service_assignments import APIServiceAssignments
from .api_service_observations import APIServiceObservations
from .api_service_resolution import APIServiceResolution
from .api_service_custody import APIServiceCustody
from .api_service_operations import APIServiceOperations, PROVIDER
from .api_saved_records import APISavedRecords
from .api_execution_progress import APIExecutionProgress, VERSION


class APIServiceExecution(APIServiceConfiguration, APIServiceAssignments,
                          APIServiceObservations, APIServiceResolution,
                          APIServiceCustody, APIServiceOperations,
                          APISavedRecords, APIExecutionProgress):
    """Keep service-native protocols behind the shared execution interfaces."""


__all__ = ['APIServiceExecution', 'PROVIDER', 'VERSION']
