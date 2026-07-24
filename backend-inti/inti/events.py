from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
import json

EventType = Literal[
    "JobStateChanged",
    "DiffReadyForApproval",
    "TestsFinished",
    "CiStatusUpdated",
    "DeployTriggered",
    "DeployCompleted",
    "ArchitectPlanGenerated",
    "QaReviewCompleted",
    "HumanApprovalReceived",
    "JobCancelled",
]


@dataclass
class DopaEvent:
    event_type: EventType
    job_id: str
    version: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_type": self.event_type,
                "job_id": self.job_id,
                "version": self.version,
                "timestamp": self.timestamp,
                "payload": self.payload,
            }
        )

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "job_id": self.job_id,
            "version": self.version,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


def create_event(event_type: EventType, job_id: str, **payload) -> DopaEvent:
    return DopaEvent(
        event_type=event_type,
        job_id=job_id,
        payload=payload,
    )


def job_state_changed(
    job_id: str, previous_status: str, new_status: str
) -> DopaEvent:
    return create_event(
        "JobStateChanged",
        job_id,
        previous_status=previous_status,
        new_status=new_status,
    )


def diff_ready(job_id: str, diff_id: str, summary: str, files_count: int) -> DopaEvent:
    return create_event(
        "DiffReadyForApproval",
        job_id,
        diff_id=diff_id,
        summary=summary,
        files_count=files_count,
    )


def tests_finished(job_id: str, passed: bool, total: int, failed: int) -> DopaEvent:
    return create_event(
        "TestsFinished",
        job_id,
        passed=passed,
        total=total,
        failed=failed,
    )


def ci_updated(
    job_id: str, status: str, provider: str, url: str | None = None
) -> DopaEvent:
    return create_event(
        "CiStatusUpdated",
        job_id,
        status=status,
        provider=provider,
        url=url,
    )


def deploy_triggered(job_id: str, environment: str) -> DopaEvent:
    return create_event(
        "DeployTriggered",
        job_id,
        environment=environment,
    )


def deploy_completed(job_id: str, environment: str, success: bool) -> DopaEvent:
    return create_event(
        "DeployCompleted",
        job_id,
        environment=environment,
        success=success,
    )


def architect_plan_generated(job_id: str, steps_count: int, estimated_files: int) -> DopaEvent:
    return create_event(
        "ArchitectPlanGenerated",
        job_id,
        steps_count=steps_count,
        estimated_files=estimated_files,
    )


def qa_review_completed(job_id: str, passed: bool, score: float) -> DopaEvent:
    return create_event(
        "QaReviewCompleted",
        job_id,
        passed=passed,
        score=score,
    )


def human_approval(job_id: str, decision: str, device_id: str) -> DopaEvent:
    return create_event(
        "HumanApprovalReceived",
        job_id,
        decision=decision,
        device_id=device_id,
    )
