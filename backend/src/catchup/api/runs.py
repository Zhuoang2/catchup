"""Start and inspect background digest runs."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from catchup.db import get_session
from catchup.digest.runner import active_run, run_detail, start_run
from catchup.errors import AppError
from catchup.models import DigestRun

router = APIRouter(prefix="/api/digest-runs")


@router.post("", status_code=202)
def create_run(request: Request) -> dict:
    run = start_run(request.app)
    with request.app.state.session_factory() as session:
        return run_detail(session, run)


@router.get("/active")
def get_active(session: Session = Depends(get_session)) -> dict | None:
    run = active_run(session)
    return run_detail(session, run) if run else None


@router.get("/{run_id}")
def get_run(run_id: int, session: Session = Depends(get_session)) -> dict:
    run = session.get(DigestRun, run_id)
    if run is None:
        raise AppError("not_found", "Run not found.", 404)
    return run_detail(session, run)
