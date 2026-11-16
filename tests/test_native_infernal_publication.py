"""Retained native bytes through the bounded worker and actual Store publication.

Store bindings, mutations and composed envelopes are explicit engineering test
inputs. None of these tests invokes Infernal or an episode/model/controller.
"""
import hashlib


from gene_annotation_episode.episodic_workflow.root.library.infernal_native_result_views import NATIVE_INFERNAL_METRICS
from gene_annotation_episode.state import Store


def test_all_native_quantities_have_store_measurement_names():
    from gene_annotation_episode.domain import METRIC_NAMES
    assert set().union(*NATIVE_INFERNAL_METRICS.values()) <= set(METRIC_NAMES)


def values(row):
    return {v["name"]: v["value"] for v in row["measurements"]}


