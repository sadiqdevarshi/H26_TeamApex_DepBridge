"""Version 1 frontend contract and the narrow engine return contract."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    # Surface integration mismatches instead of silently discarding engine evidence.
    model_config = ConfigDict(extra="forbid")


class CreateAnalysis(Contract):
    repository_url: str = Field(max_length=300)
    ref: str | None = Field(default=None, max_length=200)

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, value):
        if value is not None and (not value.strip() or value.startswith("-") or any(ord(c) < 32 for c in value)):
            raise ValueError("ref must be a nonempty branch, tag, or commit without control characters")
        return value


class CreateVerification(Contract):
    finding_id: str = Field(min_length=1, max_length=100)
    candidate_id: str = Field(min_length=1, max_length=100)


class Environment(Contract):
    python_version: str | None = None
    platform: str | None = None
    package_versions: dict[str, str] = Field(default_factory=dict)
    original_dependency_version: str | None = None
    candidate_dependency_version: str | None = None


class Coverage(Contract):
    scanned_files: int | None = Field(default=None, ge=0)
    excluded_files: int | None = Field(default=None, ge=0)
    considered_files: int | None = Field(default=None, ge=0)
    unsupported_formats: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class Summary(Contract):
    dependencies_discovered: int | None = Field(default=None, ge=0)
    dependencies_flagged: int | None = Field(default=None, ge=0)
    migration_proposals: int | None = Field(default=None, ge=0)
    completed_comparisons: int = Field(default=0, ge=0)


class Error(Contract):
    code: str
    message: str
    retryable: bool = False


class AI(Contract):
    model_name: str | None = None
    model_version: str | None = None
    access_method: str | None = None
    state: Literal["not_run", "running", "completed", "failed", "unavailable"] = "not_run"
    error: Error | None = None


class Declaration(Contract):
    path: str
    requirement: str
    name: str | None = None
    specifier: str | None = None
    marker: str | None = None
    group: str | None = None


class Evidence(Contract):
    evidence_id: str | None = None
    kind: str
    title: str
    url: str | None = None
    source_path: str | None = None
    observation: str
    retrieved_at: str | None = None


class Usage(Contract):
    path: str
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    symbol: str | None = None
    excerpt: str | None = None


class Candidate(Contract):
    candidate_id: str | None = None
    replacement_name: str | None = None
    approach: str | None = None
    rationale: str
    migration_steps: list[str] = Field(default_factory=list)
    suggested_checks: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    recommendation_source: str
    evidence_ids: list[str] = Field(default_factory=list)
    verification_supported: bool = False
    unsupported_reason: str | None = None


class Finding(Contract):
    finding_id: str | None = None
    dependency_name: str
    declarations: list[Declaration]
    risk_type: str
    title: str
    explanation: str
    evidence_strength: Literal["confirmed", "needs_review"]
    evidence: list[Evidence]
    usage: list[Usage]
    candidates: list[Candidate]
    limitations: list[str] = Field(default_factory=list)


class EngineRepository(Contract):
    revision: str | None


class AnalysisResult(Contract):
    # The engine returns observations, not job status, IDs, URLs or timestamps.
    repository: EngineRepository
    outcome: Literal["success", "partial"]
    environment: Environment
    coverage: Coverage
    summary: Summary
    ai: AI
    findings: list[Finding]
    warnings: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def honest_success(self):
        if self.outcome == "success" and not self.repository.revision:
            raise ValueError("success requires an exact repository revision")
        return self


class CheckSide(Contract):
    status: Literal["passed", "failed", "blocked", "not_run", "skipped"]
    exit_code: int | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    log_excerpt: str | None = None
    log_truncated: bool = False
    command: list[str] | None = None

    @model_validator(mode="after")
    def validate_exit(self):
        if self.status == "passed" and self.exit_code != 0:
            raise ValueError("passed check requires exit_code 0")
        return self


class Check(Contract):
    check_id: str | None = None
    name: str
    scope: Literal["installation", "focused", "full_suite"]
    original: CheckSide
    candidate: CheckSide
    comparison_note: str | None = None
    observed_match: bool | None = None


class VerificationResult(Contract):
    outcome: Literal["supported", "differences_found", "inconclusive"]
    environment: Environment
    checks: list[Check]
    limitations: list[str] = Field(default_factory=list)
    error: Error | None = None
    patch_path: str | None = None
    artifacts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def honest_supported(self):
        if self.outcome == "supported" and (not self.checks or any(
            side.status != "passed" for check in self.checks for side in (check.original, check.candidate)
        )):
            raise ValueError("supported requires actual passing original and candidate checks")
        return self
