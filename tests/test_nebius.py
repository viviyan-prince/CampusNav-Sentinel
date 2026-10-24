"""Tests for Nebius AI integration."""

from __future__ import annotations

import pytest

from app.nebius_client import NebiusAnalysis, NebiusClient


def test_nebius_client_disabled_without_key():
    """Client should be disabled when no API key is provided."""
    client = NebiusClient(api_key=None)
    assert not client.enabled


def test_nebius_client_enabled_with_key():
    """Client should be enabled when API key is provided."""
    client = NebiusClient(api_key="fake_key_for_test")
    assert client.enabled


def test_nebius_analysis_fallback_no_key():
    """Should return error analysis when API key is missing."""
    client = NebiusClient(api_key=None)
    detections = [
        {"class": "person", "confidence": 0.85, "x": 100, "y": 200},
    ]
    metadata = {
        "frame_index": 0,
        "timestamp_ms": 0.0,
        "hazard_state": "CLEAR",
        "hazard_score": 0.0,
    }

    result = client.analyze_scene(detections, metadata)

    assert isinstance(result, NebiusAnalysis)
    assert not result.success
    assert result.error is not None
    assert "API key not configured" in result.error
    assert result.scene_description == "Nebius AI disabled (no API key)"


def test_nebius_prompt_building():
    """Prompt should include detection and metadata information."""
    client = NebiusClient(api_key="fake_key")

    detections = [
        {"class": "person", "confidence": 0.85, "x": 100, "y": 200},
        {"class": "car", "confidence": 0.75, "x": 300, "y": 400},
    ]
    metadata = {
        "frame_index": 42,
        "timestamp_ms": 1400.0,
        "hazard_state": "CONFIRMED_HAZARD",
        "hazard_score": 0.65,
    }

    prompt = client._build_prompt(detections, metadata)

    assert "person" in prompt
    assert "car" in prompt
    assert "0.85" in prompt
    assert "0.75" in prompt
    assert "42" in prompt
    assert "1400" in prompt
    assert "CONFIRMED_HAZARD" in prompt
    assert "0.65" in prompt


def test_nebius_prompt_no_detections():
    """Prompt should handle empty detection list."""
    client = NebiusClient(api_key="fake_key")

    detections = []
    metadata = {
        "frame_index": 0,
        "timestamp_ms": 0.0,
        "hazard_state": "CLEAR",
        "hazard_score": 0.0,
    }

    prompt = client._build_prompt(detections, metadata)

    assert "No objects detected" in prompt


def test_nebius_response_parsing():
    """Should parse structured response correctly."""
    client = NebiusClient(api_key="fake_key")

    response = """
SCENE: Pedestrian crossing in front of shuttle
RISK: Medium - pedestrian in path
ACTION: Slow down and prepare to stop
"""

    scene, risk, action = client._parse_response(response)

    assert scene == "Pedestrian crossing in front of shuttle"
    assert risk == "Medium - pedestrian in path"
    assert action == "Slow down and prepare to stop"


def test_nebius_response_parsing_partial():
    """Should handle partial or malformed responses."""
    client = NebiusClient(api_key="fake_key")

    response = "SCENE: Clear road ahead"

    scene, risk, action = client._parse_response(response)

    assert scene == "Clear road ahead"
    assert risk == "Unknown"
    assert action == "Continue monitoring"


def test_nebius_response_parsing_empty():
    """Should provide defaults for empty response."""
    client = NebiusClient(api_key="fake_key")

    response = ""

    scene, risk, action = client._parse_response(response)

    assert scene == "Unknown"
    assert risk == "Unknown"
    assert action == "Continue monitoring"


@pytest.mark.skipif(
    not NebiusClient(api_key=None).api_key,
    reason="NEBIUS_API_KEY not set",
)
def test_nebius_real_api_call():
    """Test with real Nebius API (requires NEBIUS_API_KEY env var)."""
    client = NebiusClient()  # Uses env var

    if not client.enabled:
        pytest.skip("Nebius API key not configured")

    detections = [
        {"class": "person", "confidence": 0.85, "x": 320, "y": 400},
    ]
    metadata = {
        "frame_index": 5,
        "timestamp_ms": 333.0,
        "hazard_state": "POSSIBLE_HAZARD",
        "hazard_score": 0.45,
    }

    result = client.analyze_scene(detections, metadata)

    # Should succeed with real API
    assert result.success
    assert result.error is None
    assert len(result.scene_description) > 0
    assert len(result.risk_assessment) > 0
    assert len(result.recommendations) > 0
    assert result.model_used == client.model
