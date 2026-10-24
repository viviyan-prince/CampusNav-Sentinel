"""Nebius AI Cloud integration for scene analysis."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NebiusAnalysis:
    """Scene analysis result from Nebius AI."""

    raw_response: str
    scene_description: str
    risk_assessment: str
    recommendations: str
    model_used: str
    success: bool
    error: Optional[str] = None


class NebiusClient:
    """Client for Nebius AI Cloud inference using NVIDIA models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.studio.nebius.ai/v1/",
        model: str = "meta-llama/Llama-3.3-70B-Instruct",
        timeout: int = 30,
    ):
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY")
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.warning("Nebius API key not found. Scene analysis will be disabled.")

    def analyze_scene(
        self,
        detections: list[dict],
        frame_metadata: dict,
    ) -> NebiusAnalysis:
        """Analyze detected objects and scene context using Nebius AI."""

        if not self.enabled:
            return NebiusAnalysis(
                raw_response="",
                scene_description="Nebius AI disabled (no API key)",
                risk_assessment="Unknown",
                recommendations="Configure NEBIUS_API_KEY to enable scene analysis",
                model_used="none",
                success=False,
                error="API key not configured",
            )

        try:
            # Import here to avoid requiring openai when not using Nebius
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

            # Build context prompt from detections
            prompt = self._build_prompt(detections, frame_metadata)

            # Call Nebius AI via OpenAI-compatible API
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a campus shuttle safety assistant. Analyze detected objects "
                            "and scene context to assess risks and provide actionable recommendations. "
                            "Be concise and specific."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=400,
                timeout=self.timeout,
            )

            raw_text = response.choices[0].message.content or ""

            # Parse response
            scene_desc, risk_assess, recomm = self._parse_response(raw_text)

            return NebiusAnalysis(
                raw_response=raw_text,
                scene_description=scene_desc,
                risk_assessment=risk_assess,
                recommendations=recomm,
                model_used=self.model,
                success=True,
            )

        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return NebiusAnalysis(
                raw_response="",
                scene_description="Error: openai package not installed",
                risk_assessment="Unknown",
                recommendations="Run: pip install openai",
                model_used=self.model,
                success=False,
                error="Missing dependency: openai",
            )
        except Exception as e:
            logger.error("Nebius API call failed: %s", e)
            return NebiusAnalysis(
                raw_response="",
                scene_description=f"Nebius API error: {type(e).__name__}",
                risk_assessment="Unknown",
                recommendations="Check API key and network connection",
                model_used=self.model,
                success=False,
                error=str(e),
            )

    def _build_prompt(self, detections: list[dict], metadata: dict) -> str:
        """Build analysis prompt from detections and metadata."""

        det_summary = []
        for d in detections:
            det_summary.append(
                f"- {d['class']} (confidence {d['confidence']:.2f}) "
                f"at position {d['x']:.0f},{d['y']:.0f}"
            )

        det_text = "\n".join(det_summary) if det_summary else "No objects detected"

        prompt = f"""Analyze this campus shuttle camera frame:

**Frame Context:**
- Frame index: {metadata.get('frame_index', 0)}
- Timestamp: {metadata.get('timestamp_ms', 0):.0f}ms
- Current hazard state: {metadata.get('hazard_state', 'UNKNOWN')}
- Hazard score: {metadata.get('hazard_score', 0):.2f}

**Detected Objects:**
{det_text}

**Analysis Required:**
1. Scene Description: What is happening in this frame?
2. Risk Assessment: What are the safety risks (low/medium/high)?
3. Recommendations: What should the shuttle operator do?

Format your response as:
SCENE: [description]
RISK: [assessment]
ACTION: [recommendations]
"""
        return prompt

    def _parse_response(self, text: str) -> tuple[str, str, str]:
        """Parse structured response from model output."""

        scene = "Unknown"
        risk = "Unknown"
        action = "Continue monitoring"

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("SCENE:"):
                scene = line[6:].strip()
            elif line.startswith("RISK:"):
                risk = line[5:].strip()
            elif line.startswith("ACTION:"):
                action = line[7:].strip()

        return scene, risk, action
