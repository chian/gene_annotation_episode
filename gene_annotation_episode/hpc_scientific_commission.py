"""Describe one frozen scientific work unit for the existing HPC owner.

This supplies explicit initial portfolios and broad uncalibrated priors. The
HPC parent and its sisters own planning, refinement, launch and monitoring.
"""
import math

from .execution_guidance import resource_identity
from .hpc_queue import digest


def commission(*, resource_id, resource, tool, request_sha256, worker_sha256,
               implementation_sha256, parameters, files, worker_name, request_name,
               program, version, features, preparation, objective):
    root = '{allocation_workspace}'
    features = {'nodes': 1, 'wall_seconds': 900, **features}
    hardware = resource_identity(resource_id, resource)
    predicates = [{'field':[key], 'operator':'eq', 'value':value} for key,value in (
        ('program',program),('version',version),('completed',True),('returncode',0),
        ('request_sha256',request_sha256),('worker_sha256',worker_sha256),
        ('code_manifest_sha256',implementation_sha256))]
    return {'objective':objective,'resource_id':resource_id,
        'execution_profile':{'resource_id':hardware,'backend':'hpc','tool':tool,
            'implementation':implementation_sha256,'parameters':digest(parameters),'hardware':hardware},
        'monitoring':{'min_interval_seconds':60.,'max_interval_seconds':120.,'monitor_cost':.001},
        'obligations':{'scientific_result':{'credit':1.,'acceptance':predicates}},
        'candidates':[{'id':tool.replace('.','_')+'_'+request_sha256[:16], 'queue':'debug',
            'nodes':1,'wall_seconds':900,'features':features,
            'units':[{'unit_id':'scientific_result','obligation_id':'scientific_result','effort':1.,
                'argv':[resource['python_executable'],'-B',root+'/'+worker_name,root+'/'+request_name],
                'environment':{'PYTHONDONTWRITEBYTECODE':'1'}}],
            'files':[{'path':name,'text':text} for name,text in files.items()], 'preparation':preparation}],
        'model':{'features':[{'name':key,'transform':'log1p','scale':math.log1p(max(1,value))}
                for key,value in features.items()],
            'priors':{key:{'median_seconds':value,'log_sigma':2.,'coefficient_variance':.01}
                for key,value in {'queue':900.,'setup':30.,'work':60.,'return':10.}.items()},
            'resource_priors':{'cpu_seconds':{'median':60.,'unit':'cpu_seconds','log_sigma':2.,'coefficient_variance':.01},
                'memory_bytes':{'median':512*1024**2,'unit':'bytes','log_sigma':2.,'coefficient_variance':.01}},
            'success_prior':[1.,1.]}, 'history':[],'validation_ids':[],
        'credit':{'model_scale':.01,'validation_scale':.1,'validation_slots':[
            {'id':'planned_'+key,'metric':key,'phase':'planned','minimum_elapsed_seconds':0.,'weight':1.}
            for key in ('queue','work','cpu_seconds','memory_bytes')]},
        'preferences':{'elapsed_cost_per_second':.00001,'node_hour_cost':.01},
        'limits':{'result_limit_bytes':512*1024,'queue_max_age_seconds':900}}
