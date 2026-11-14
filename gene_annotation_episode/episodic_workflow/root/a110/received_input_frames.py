"""A110 original commission selection and frozen form readers."""
import json
import math
from jsonschema import Draft202012Validator, ValidationError
from .communication import plain, validate_closed_schema
from .episode_contract_information import expand_fact_form, validate_saved_fact_form
from .episode_return_records import EpisodeReturnRecords

_PREFIX = "a110_received_input_frame_"

class ReceivedInputFrameError(ValueError):
    """Stable, operand-free failure information for the consuming host."""

    def __init__(self, code, *, path=""):
        self.code = _PREFIX + code
        self.diagnostics = [{"code": self.code, "path": path}]
        super().__init__(self.code)


class ReceivedInputFrames(EpisodeReturnRecords):
    def __init__(self, store, run_id):
        super().__init__(store, run_id, failure_prefix=_PREFIX)
        self._require(type(run_id) is str and bool(run_id), "run_id_required")

    def _require(self, condition, code):
        if not condition:
            raise ReceivedInputFrameError(code)

    def _json(self, raw):
        def pairs(items):
            result = {}
            for key, value in items:
                self._require(key not in result, "duplicate_json_member")
                result[key] = value
            return result

        def number(value):
            result = float(value)
            self._require(math.isfinite(result), "nonfinite_json")
            return result

        def constant(_):
            raise ReceivedInputFrameError("nonfinite_json")

        try:
            return json.loads(raw, object_pairs_hook=pairs, parse_float=number,
                              parse_constant=constant)
        except ReceivedInputFrameError:
            raise
        except (ValueError, TypeError, UnicodeError, RecursionError) as error:
            raise ReceivedInputFrameError("invalid_json") from error

    def _table(self, name):
        return self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                               (name,)).fetchone() is not None

    def _contract_information(self, sent):
        """Validate only the original frame; never consult a current factory."""
        from .runtime import Workflow
        from .episode_journal import WorkflowError
        try:
            return Workflow.validate_contract_information(None, sent)
        except (WorkflowError, ValueError, TypeError, KeyError, IndexError,
                AttributeError, RecursionError) as error:
            raise ReceivedInputFrameError("original_contract_information_conflict") from error

    def _selection(self, parent, index, *, unsaved=False):
        """Read the exact original selection and its optional frozen frame."""
        action = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? AND decision_index=?", (self.run_id, parent.episode_id, index)).fetchone()
        call = self.db.execute("SELECT request,response,purpose FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND call_index=?", (self.run_id, parent.episode_id, index)).fetchone()
        selected = None if action is None else self._json(action["action"])
        model, sent = None, None
        if call is not None:
            self._require(call["purpose"] == "decision", "parent_selection_purpose_conflict")
            sent = self._json(call["request"])
            self._require(type(sent) is dict and type(sent.get("schema")) is dict,
                          "parent_selection_schema_required")
            if "contract_information" in sent:
                self._contract_information(sent)
        if call is not None and call["response"] is not None:
            response = self._json(call["response"])
            self._require(type(response) is dict, "parent_selection_schema_required")
            candidate = response.get("selection")
            if type(candidate) is dict and type(candidate.get("assignment")) is str:
                self._json(candidate["assignment"])
            # Reuse the runtime's exact transport normalization and the saved
            # original schema; today's catalog never rewrites old selections.
            from .runtime import _decode_recorded_action_response, _recorded_assignment_transport
            try:
                exchanges = []
                if selected is None and self._table('runtime_decision_exchanges'):
                    exchanges = [{'request': self._json(row['request']),
                        'response': self._json(row['response']), 'response_recorded': True}
                        for row in self.db.execute('SELECT request,response FROM runtime_decision_exchanges '
                            'WHERE run_id=? AND episode_id=? AND decision_index=? AND response IS NOT NULL '
                            'ORDER BY exchange_index', (self.run_id, parent.episode_id, index))]
                model = _decode_recorded_action_response(response, sent["schema"],
                    recorded_selection=selected, exchanges=exchanges,
                    exchange_schema=sent.get('contract_information', {}).get('exchange_schema'),
                    unproven_replay=not _recorded_assignment_transport(sent)).get("selection")
                Draft202012Validator(sent["schema"]["properties"]["selection"]).validate(model)
            except (ValidationError, ValueError, TypeError, KeyError, AttributeError) as error:
                raise ReceivedInputFrameError("parent_selection_conflict" if str(error) ==
                    'original_action_response_selection_mismatch' else "parent_selection_invalid") from error
        self._require(model is not None if unsaved else selected is not None or model is not None,
                      "saved_parent_selection_required")
        if selected is not None and model is not None:
            self._require(self._equal(selected, model), "parent_selection_conflict")
        selected = model if selected is None else selected
        self._require(type(selected) is dict, "parent_selection_invalid")
        if sent is not None and model is None:
            try:
                Draft202012Validator(sent["schema"]["properties"]["selection"]).validate(selected)
            except (ValidationError, ValueError, TypeError, KeyError) as error:
                raise ReceivedInputFrameError("parent_selection_invalid") from error
        return selected, sent

    def _selected_form(self, selected, role, sent):
        """Expand from a frozen frame already authenticated by _selection."""
        try:
            if sent is None or "contract_information" not in sent:
                return {"expanded_schema": validate_closed_schema(self._json(selected["schema_json"])),
                        "declaration": None}
            record = sent["contract_information"]
            facts = {key: {source: row for source, row in rows.items() if "report_schema" in row}
                     for key, rows in record["fact_sources_by_role"].items()}
            return expand_fact_form(selected["schema_json"], child_role=role, facts_by_role=facts,
                                    permitted_child_roles=record["permitted_child_roles"])
        except ReceivedInputFrameError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
            raise ReceivedInputFrameError("commission_contract_invalid") from error

    @staticmethod
    def _report_contract(purpose, schema):
        return {"decision": purpose, "measurements": {"schema": schema},
            "information": {key: node.get("description", key) for key, node in schema["properties"].items()}}

    def _child_contract(self, context, selected, sent):
        result = self._selected_form(selected, context.role, sent)
        request = plain(context.request)
        declaration = request["message"].get("report_contract_declaration")
        self._require(("report_contract_declaration" in request["message"]) == (result["declaration"] is not None)
            and self._equal(declaration, result["declaration"]), "commission_declaration_conflict")
        if declaration is not None:
            try:
                validate_saved_fact_form(child_role=context.role, submitted_schema_json=selected["schema_json"],
                    expanded_schema=request["report_contract"]["measurements"]["schema"], declaration=declaration)
            except (ValueError, TypeError, KeyError) as error:
                raise ReceivedInputFrameError("commission_contract_invalid") from error
        schema = result["expanded_schema"]
        self._require(self._equal(request.get("report_contract"),
            self._report_contract(selected.get("purpose"), schema)), "commission_contract_conflict")
        return schema

