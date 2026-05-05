"""HTTP API routes for the Rakkib web runtime."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from rakkib.normalize import eval_when
from rakkib.schema import FieldDef, QuestionSchema, load_all_schemas
from rakkib.state import State

from .answers import PhaseValidationError, apply_phase_answers
from .auth import AuthManager

REDACTED_SECRET = "[redacted]"


class SessionBootstrapRequest(BaseModel):
    """Incoming bootstrap token payload."""

    token: str | None = None


class StatePatchRequest(BaseModel):
    """Generic partial state update payload."""

    state: dict[str, object] = {}


class PhaseAnswersRequest(BaseModel):
    """Phase answer submission payload."""

    answers: dict[str, object] = {}
    confirmations: dict[str, bool] = {}


def _load_state() -> State:
    """Load the persisted setup state from disk."""
    return State.load()


def _schemas() -> list[QuestionSchema]:
    """Load all question schemas in phase order."""
    return load_all_schemas()


def _redact_state_payload(state: State) -> dict[str, object]:
    """Return a redacted copy of the persisted state."""
    payload = deepcopy(state.to_dict())
    secrets = payload.get("secrets")

    if not isinstance(secrets, dict):
        return payload

    values = secrets.get("values")
    if not isinstance(values, dict):
        return payload

    for key, value in values.items():
        if value is not None:
            values[key] = REDACTED_SECRET

    return payload


def _redact_record_value(record_key: str, value: object) -> object:
    """Redact a record value when it points at stored secrets."""
    if not record_key.startswith("secrets.values"):
        return value
    if value is None:
        return None
    return REDACTED_SECRET


def _active_fields(schema: QuestionSchema, state: State) -> list[FieldDef]:
    """Return only fields whose `when` expressions are currently active."""
    active: list[FieldDef] = []

    for field in schema.fields:
        if field.when and not eval_when(field.when, state):
            continue
        active.append(field)

    return active


def _field_answers(field: FieldDef, state: State) -> object:
    """Serialize the current answer shape for one active field."""
    if field.type == "summary":
        return {
            key: _redact_record_value(key, state.get(key))
            for key in field.summary_fields
        }

    if field.type == "secret_group":
        values: dict[str, object] = {}
        for entry in field.entries:
            key = str(entry.get("key", "")).strip()
            when = str(entry.get("when", "always")).strip()

            if not key:
                continue
            if when != "always" and not eval_when(when, state):
                continue

            record_key = f"secrets.values.{key}"
            values[key] = _redact_record_value(record_key, state.get(record_key))
        return values

    if not field.records:
        return None

    if len(field.records) == 1:
        record_key = field.records[0]
        return _redact_record_value(record_key, state.get(record_key))

    return {
        record_key: _redact_record_value(record_key, state.get(record_key))
        for record_key in field.records
    }


def _serialize_phase_summary(schema: QuestionSchema, state: State) -> dict[str, object]:
    """Build the route metadata for a single setup phase."""
    return {
        "phase": schema.phase,
        "complete": state.is_phase_complete(schema.phase),
        "writes_state": schema.writes_state,
        "has_service_catalog": bool(schema.service_catalog),
        "route": f"/setup/phase/{schema.phase}",
    }


def _serialize_phase(schema: QuestionSchema, state: State) -> dict[str, object]:
    """Build the API payload for a single setup phase."""
    active_fields = _active_fields(schema, state)

    return {
        "phase": schema.phase,
        "complete": state.is_phase_complete(schema.phase),
        "reads_state": schema.reads_state,
        "writes_state": schema.writes_state,
        "fields": [_serialize_field(field, state) for field in active_fields],
        "service_catalog": schema.service_catalog,
        "rules": schema.rules,
        "execution_generated_only": schema.execution_generated_only,
        "answers": {
            field.id: _field_answers(field, state)
            for field in active_fields
        },
    }


def _serialize_field(field: FieldDef, state: State) -> dict[str, object]:
    """Serialize one field with active secret entries only."""
    payload = asdict(field)
    if field.type != "secret_group":
        return payload

    payload["entries"] = [
        entry
        for entry in field.entries
        if str(entry.get("when", "always")).strip() == "always"
        or eval_when(str(entry.get("when", "always")).strip(), state)
    ]
    return payload


def build_api_router(auth: AuthManager) -> APIRouter:
    """Create the minimal API router for the current web phase."""
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, bool | str]:
        return {
            "ok": True,
            "auth_enabled": auth.token_auth_enabled,
            "mode": "token" if auth.token_auth_enabled else "open",
        }

    @router.post("/session/bootstrap")
    def session_bootstrap(payload: SessionBootstrapRequest, response: Response) -> dict[str, bool | str]:
        response.headers["Cache-Control"] = "no-store"

        if not auth.validate_token(payload.token):
            response.status_code = 401
            return {
                "ok": False,
                "message": (
                    "This setup token is invalid or expired. Open the printed setup URL again or run "
                    "`rakkib web --lan` to generate a fresh token."
                ),
            }

        session_id = auth.issue_session()
        auth.set_session_cookie(response, session_id)
        return {"ok": True}

    @router.get("/session")
    def session_status(request: Request, response: Response) -> dict[str, bool]:
        auth.require_api_auth(request)
        response.headers["Cache-Control"] = "no-store"
        return {
            "authenticated": True,
            "auth_enabled": auth.token_auth_enabled,
        }

    @router.get("/state")
    def state_payload(request: Request, response: Response) -> dict[str, object]:
        auth.require_api_auth(request)
        response.headers["Cache-Control"] = "no-store"

        state = _load_state()
        return {
            "state": _redact_state_payload(state),
            "confirmed": state.is_confirmed(),
            "resume_phase": state.resume_phase(),
        }

    @router.patch("/state")
    def patch_state(payload: StatePatchRequest, request: Request, response: Response) -> dict[str, object]:
        auth.require_api_auth(request)
        response.headers["Cache-Control"] = "no-store"

        state = _load_state()
        state.merge(payload.state)
        state.save()

        return {
            "state": _redact_state_payload(state),
            "confirmed": state.is_confirmed(),
            "resume_phase": state.resume_phase(),
        }

    @router.get("/state/resume")
    def state_resume(request: Request, response: Response) -> dict[str, object]:
        auth.require_api_auth(request)
        response.headers["Cache-Control"] = "no-store"

        state = _load_state()
        schemas = _schemas()

        return {
            "resume_phase": state.resume_phase(),
            "confirmed": state.is_confirmed(),
            "phases": [_serialize_phase_summary(schema, state) for schema in schemas],
        }

    @router.get("/questions/phases")
    def question_phases(request: Request, response: Response) -> dict[str, object]:
        auth.require_api_auth(request)
        response.headers["Cache-Control"] = "no-store"

        state = _load_state()
        schemas = _schemas()

        return {
            "phases": [_serialize_phase_summary(schema, state) for schema in schemas],
        }

    @router.get("/questions/phases/{phase}")
    def question_phase(phase: int, request: Request, response: Response) -> dict[str, object]:
        auth.require_api_auth(request)
        response.headers["Cache-Control"] = "no-store"

        state = _load_state()
        schema = next((item for item in _schemas() if item.phase == phase), None)
        if schema is None:
            raise HTTPException(status_code=404, detail=f"Unknown phase: {phase}")

        return _serialize_phase(schema, state)

    @router.post("/questions/phases/{phase}/answers")
    def submit_phase_answers(
        phase: int,
        payload: PhaseAnswersRequest,
        request: Request,
        response: Response,
    ) -> dict[str, object]:
        auth.require_api_auth(request)
        response.headers["Cache-Control"] = "no-store"

        current_state = _load_state()
        schema = next((item for item in _schemas() if item.phase == phase), None)
        if schema is None:
            raise HTTPException(status_code=404, detail=f"Unknown phase: {phase}")

        try:
            updated_state = apply_phase_answers(
                current_state,
                schema,
                payload.answers,
                confirmations=payload.confirmations,
            )
        except PhaseValidationError as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": error.message,
                    "field_errors": error.field_errors,
                },
            ) from error

        updated_state.save()

        return {
            "ok": True,
            "phase": _serialize_phase(schema, updated_state),
            "resume_phase": updated_state.resume_phase(),
            "confirmed": updated_state.is_confirmed(),
        }

    return router
