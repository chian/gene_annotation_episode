"""Mutable original family custody shared by its three fixed implementations."""

def get_jobs(self):
    return self._custody.jobs

def set_jobs(self, value):
    self._custody.jobs = value

jobs = property(get_jobs, set_jobs)

def get_parser_policy(self):
    return self._custody.parser_policy

def set_parser_policy(self, value):
    self._custody.parser_policy = value

parser_policy = property(get_parser_policy, set_parser_policy)

def get__job_credit_calculator(self):
    return self._custody._job_credit_calculator

def set__job_credit_calculator(self, value):
    self._custody._job_credit_calculator = value

_job_credit_calculator = property(get__job_credit_calculator, set__job_credit_calculator)

def get_monitoring_projector(self):
    return self._custody.monitoring_projector

def set_monitoring_projector(self, value):
    self._custody.monitoring_projector = value

monitoring_projector = property(get_monitoring_projector, set_monitoring_projector)

def get__role_credit_bindings(self):
    return self._custody._role_credit_bindings

def set__role_credit_bindings(self, value):
    self._custody._role_credit_bindings = value

_role_credit_bindings = property(get__role_credit_bindings, set__role_credit_bindings)

def get_statistics(self):
    return self._custody.statistics

def set_statistics(self, value):
    self._custody.statistics = value

statistics = property(get_statistics, set_statistics)

def get_native_event_provider(self):
    return self._custody.native_event_provider

def set_native_event_provider(self, value):
    self._custody.native_event_provider = value

native_event_provider = property(get_native_event_provider, set_native_event_provider)

