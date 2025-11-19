#!/usr/bin/env python3
"""
MONAI Medical Imaging Tool for CrewAI
Wraps medical_imaging.py for use by imaging_agent
"""

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.services.monai_chexnet import get_imaging_pipeline


class MonaiToolInput(BaseModel):
    """Input schema for MONAI imaging analyzer"""
    image_path: str = Field(..., description="Path to DICOM or image file")
    modality: str = Field(default="XR", description="Imaging modality: XR (X-ray), CT, or MRI")


class MonaiTool(BaseTool):
    """
    Medical Imaging Analyzer using MONAI + CheXNet

    Analyzes chest X-rays, CT scans, and MRI images using deep learning models.
    Returns findings, confidence scores, and differential diagnoses.

    Used by: imaging_agent (Radiology Agent)
    """

    name: str = "MONAI Medical Imaging Analyzer"
    description: str = """Analyze medical images (X-ray, CT, MRI) using MONAI and CheXNet AI models.
    Detects 14 pathologies in chest X-rays including pneumonia, effusion, cardiomegaly, etc.
    Returns findings with confidence scores and differential diagnosis."""
    args_schema: Type[BaseModel] = MonaiToolInput

    def _run(self, image_path: str, modality: str = "XR") -> str:
        """
        Analyze medical image using MONAI/CheXNet pipeline

        Args:
            image_path: Path to DICOM or image file
            modality: XR (X-ray), CT, or MRI

        Returns:
            Structured findings report for imaging_agent
        """
        try:
            pipeline = get_imaging_pipeline()
            result = pipeline.analyze_image(image_path, modality=modality)

            findings = result.get('findings', [])
            confidence = result.get('confidence', 0.0)
            differential = result.get('differential_diagnosis', [])
            heatmap = result.get('heatmap_path', 'N/A')

            output = f"""=== IMAGING ANALYSIS ({modality}) ===

Findings: {', '.join(findings) if findings else 'No significant findings'}

Confidence: {confidence:.1%}

Differential Diagnosis:
{chr(10).join(f'  - {dx}' for dx in differential[:3]) if differential else '  - None'}

Heatmap: {heatmap}

Recommendation: {self._get_recommendation(findings, confidence)}
"""
            return output

        except Exception as e:
            return f"""=== IMAGING ANALYSIS FAILED ===
Error: {str(e)}

Recommendation: REQUIRE RADIOLOGIST REVIEW
This AI analysis could not complete. Manual review is mandatory.
"""

    def _get_recommendation(self, findings: list, confidence: float) -> str:
        """Generate clinical recommendation based on findings"""
        if not findings:
            return "No actionable findings. Routine follow-up."

        if confidence < 0.7:
            return "Low confidence. Recommend radiologist confirmation."

        critical_findings = ['pneumothorax', 'pulmonary edema', 'massive effusion']
        if any(critical in ' '.join(findings).lower() for critical in critical_findings):
            return "CRITICAL FINDINGS. Immediate radiologist consultation required."

        return "Positive findings detected. Radiologist review recommended."


# Export
__all__ = ['MonaiTool']


if __name__ == "__main__":
    print("MONAI Tool - Medical Imaging Analyzer")
    print("=" * 50)

    tool = MonaiTool()
    print(f"Tool Name: {tool.name}")
    print(f"Description: {tool.description}")
    print("\nThis tool wraps MONAI/CheXNet for use by CrewAI imaging_agent")
