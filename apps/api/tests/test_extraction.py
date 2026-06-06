"""Tests for app.models.extraction — Pydantic model validation."""

import pytest
from pydantic import ValidationError

from app.models.extraction import ExtractedTask, ProjectResolution

# Prompt examples A–D as raw dicts (mirrors task-extraction.md §Examples)

EXAMPLE_A = {
    "intent": "task_creation",
    "owner": "Mateo",
    "task_title": "Preparar informe para financiador",
    "description": None,
    "due_date": "2026-06-12",
    "status": "pending",
    "priority": "high",
    "confidence": 0.93,
    "is_global": False,
    "project_resolution": {
        "status": "matched",
        "project_id": "p1111111-1111-1111-1111-111111111111",
        "project_name_matched": "Informe financiador Q2",
        "confidence": 0.88,
        "reason": "Menciona informe del financiador; coincide con un solo proyecto activo.",
    },
    # scope_reason intentionally omitted (example A in the prompt omits it)
    "ambiguities": [],
}

EXAMPLE_B = {
    "intent": "task_creation",
    "owner": "Laura",
    "task_title": "Renovar certificado SSL del sitio",
    "description": None,
    "due_date": "2026-06-20",
    "status": "pending",
    "priority": "urgent",
    "confidence": 0.9,
    "is_global": False,
    "project_resolution": {
        "status": "standalone",
        "project_id": None,
        "project_name_matched": None,
        "confidence": 0.85,
        "reason": "Trámite técnico puntual; no referencia ningún proyecto activo.",
    },
    "ambiguities": [],
}

EXAMPLE_C = {
    "intent": "task_creation",
    "owner": "Ana",
    "task_title": "Coordinar espacio para el taller",
    "description": None,
    "due_date": "2026-06-07",
    "status": "pending",
    "priority": "normal",
    "confidence": 0.87,
    "is_global": False,
    "project_resolution": {
        "status": "needs_clarification",
        "project_id": None,
        "project_name_matched": None,
        "confidence": 0.45,
        "reason": "Menciona taller pero podría ser del proyecto Taller nutrición o tarea suelta.",
    },
    "ambiguities": ["No queda claro si el taller pertenece a un proyecto formal."],
}

EXAMPLE_D = {
    "intent": "task_creation",
    "owner": "Laura",
    "task_title": "Renovar personería jurídica de la fundación",
    "description": None,
    "due_date": "2026-09-01",
    "status": "pending",
    "priority": "high",
    "confidence": 0.92,
    "is_global": True,
    "project_resolution": {
        "status": "not_applicable",
        "project_id": None,
        "project_name_matched": None,
        "confidence": 1.0,
        "reason": "Trámite institucional de toda la ONG.",
    },
    "scope_reason": "Afecta a la organización en su conjunto, no a un proyecto operativo.",
    "ambiguities": [],
}


@pytest.mark.parametrize("payload", [EXAMPLE_A, EXAMPLE_B, EXAMPLE_C, EXAMPLE_D])
def test_prompt_examples_parse_correctly(payload):
    task = ExtractedTask.model_validate(payload)
    assert task.intent == "task_creation"
    assert 0.0 <= task.confidence <= 1.0


def test_example_a_matched():
    task = ExtractedTask.model_validate(EXAMPLE_A)
    assert task.is_global is False
    assert task.project_resolution.status == "matched"
    assert task.project_resolution.project_id == "p1111111-1111-1111-1111-111111111111"
    assert task.scope_reason is None  # omitted → defaults to None


def test_example_d_global():
    task = ExtractedTask.model_validate(EXAMPLE_D)
    assert task.is_global is True
    assert task.project_resolution.status == "not_applicable"
    assert task.project_resolution.project_id is None
    assert task.scope_reason == "Afecta a la organización en su conjunto, no a un proyecto operativo."


def test_invalid_priority_rejected():
    bad = {**EXAMPLE_A, "priority": "extreme"}
    with pytest.raises(ValidationError):
        ExtractedTask.model_validate(bad)


def test_invalid_project_resolution_status_rejected():
    bad = {
        **EXAMPLE_A,
        "project_resolution": {**EXAMPLE_A["project_resolution"], "status": "unknown"},
    }
    with pytest.raises(ValidationError):
        ExtractedTask.model_validate(bad)


def test_invalid_task_status_rejected():
    bad = {**EXAMPLE_A, "status": "closed"}
    with pytest.raises(ValidationError):
        ExtractedTask.model_validate(bad)


def test_ambiguities_defaults_to_empty_list():
    payload = {**EXAMPLE_A}
    del payload["ambiguities"]
    task = ExtractedTask.model_validate(payload)
    assert task.ambiguities == []
