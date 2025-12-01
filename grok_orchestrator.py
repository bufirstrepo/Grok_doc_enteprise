"""
Grok AI Orchestrator - HIPAA-Compliant Multi-Vendor Comparison
Grok decides which AIs to consult, aggregates responses, makes final decision
"""


from local_inference import grok_query
from typing import List, Dict
import json
import os  # Required for XAI_API_KEY environment variable check


class GrokOrchestrator:
    """
    Grok-as-Arbiter Pattern:
    1. Grok analyzes prompt and decides which vendor AIs to consult
    2. Vendor AIs provide recommendations
    3. Grok compares all responses and makes final decision
    """
    
    def __init__(self):
        """Initialize with API key validation"""
        if not os.getenv("XAI_API_KEY"):
            raise RuntimeError(
                "🔴 FATAL: XAI_API_KEY environment variable required for production. "
                "Set: export XAI_API_KEY='your-key'"
            )
        
        self.AVAILABLE_CONSULTANTS = [
            "gpt-4-turbo",        # Azure OpenAI (HIPAA-compliant)
            "claude-3-5-sonnet",  # Anthropic Claude
            "gemini-pro",         # Google Gemini
            "llama-3.1-70b"       # Local (on-prem)
        ]
    
    def consult_and_decide(self, clinical_prompt: str) -> Dict:
        """
        Full orchestration: Grok decides, consults vendors, makes final call
        
        Returns:
            {
                "grok_routing_decision": str,
                "consultants_used": List[str],
                "consultant_responses": Dict[str, str],
                "grok_final_decision": str,
                "confidence": float
            }
        """
        
        # STEP 1: Grok decides which AIs to consult
        routing_prompt = f"""You are the orchestrator AI for a hospital's clinical decision support.
        
Clinical Question:
{clinical_prompt}

Available consultant AIs:
- gpt-4-turbo (Azure OpenAI, HIPAA-compliant, strong on general medicine)
- claude-3-5-sonnet (Anthropic, strong on reasoning and safety analysis)
- gemini-pro (Google, strong on evidence synthesis)
- llama-3.1-70b (Local on-prem, privacy-first)

Task: Decide which 2-3 AIs to consult for this case. Return ONLY a JSON list like:
["gpt-4-turbo", "claude-3-5-sonnet"]

Consider: complexity, specialty, privacy requirements."""

        grok_routing = grok_query(
            routing_prompt,
            model_name="grok-beta",
            temperature=0.0
        )
        
        
        # Parse Grok's routing decision
        try:
            consultants_to_use = json.loads(grok_routing)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # Grok failed to parse - use safe default
            print(f"⚠️ Grok routing parse error: {e}. Using default consultants.")
            consultants_to_use = self.AVAILABLE_CONSULTANTS[:3]
        
        # STEP 2: Query selected consultant AIs in parallel
        consultant_responses = {}
        for consultant_model in consultants_to_use:
            try:
                response = grok_query(
                    clinical_prompt,
                    model_name=consultant_model,
                    temperature=0.0,
                    system_prompt="You are a clinical consultant AI. Provide concise, evidence-based recommendation."
                )
                consultant_responses[consultant_model] = response
            except Exception as e:
                consultant_responses[consultant_model] = f"ERROR: {str(e)}"
        
        # STEP 3: Grok reviews all responses and makes final decision
        comparison_prompt = f"""You are the final decision-maker for clinical AI recommendations.

Original Question:
{clinical_prompt}

Consultant AI Responses:
{json.dumps(consultant_responses, indent=2)}

Task: 
1. Compare all consultant responses
2. Identify consensus vs disagreements
3. Make final clinical recommendation
4. Assign confidence score (0.0-1.0)

Return JSON:
{{
  "final_recommendation": "your decision",
  "consensus_points": ["point 1", "point 2"],
  "disagreements": ["issue 1"],
  "confidence": 0.85,
  "rationale": "why this decision"
}}"""

        grok_final = grok_query(
            comparison_prompt,
            model_name="grok-beta",
            temperature=0.0
        )
        
        return {
            "grok_routing_decision": grok_routing,
            "consultants_used": consultants_to_use,
            "consultant_responses": consultant_responses,
            "grok_final_decision": grok_final,
            "raw_grok_output": grok_final
        }

def grok_orchestrated_query(clinical_prompt: str) -> str:
    """
    Simple API: Send clinical question, get Grok's final decision
    (Grok automatically consults other AIs as needed)
    """
    orchestrator = GrokOrchestrator()
    result = orchestrator.consult_and_decide(clinical_prompt)
    
    # Return Grok's final decision
    try:
        final = json.loads(result["grok_final_decision"])
        return final.get("final_recommendation", result["grok_final_decision"])
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        # Grok's JSON malformed - return raw text
        print(f"⚠️ Grok final decision parse error: {e}")
        return result["grok_final_decision"]

# Example usage
if __name__ == "__main__":
    clinical_case = """
    Patient: 67F with new-onset AFib, CrCl 45 mL/min, recent GI bleed (3 months ago).
    Question: Anticoagulation strategy?
    """
    
    orchestrator = GrokOrchestrator()
    result = orchestrator.consult_and_decide(clinical_case)
    
    print("=" * 80)
    print("GROK ORCHESTRATION REPORT")
    print("=" * 80)
    print(f"\n1. GROK'S ROUTING DECISION:")
    print(f"   Consultants chosen: {result['consultants_used']}")
    print(f"\n2. CONSULTANT RESPONSES:")
    for model, response in result['consultant_responses'].items():
        print(f"\n   {model}:")
        print(f"   {response[:150]}...")
    print(f"\n3. GROK'S FINAL DECISION:")
    print(f"   {result['grok_final_decision']}")
