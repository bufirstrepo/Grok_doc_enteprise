"""
Multi-LLM Decision Chain for Clinical Reasoning

Implements a four-stage LLM chain where each model plays a specialized role:
1. Kinetics Model - Raw pharmacokinetic calculations
2. Adversarial Model - Devil's advocate risk analysis
3. Literature Model - Evidence-based recommendations
4. Arbiter Model - Final reconciliation and decision
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from local_inference import grok_query

@dataclass
class ChainStep:
    """Single step in the LLM reasoning chain"""
    step_name: str
    prompt: str
    response: str
    timestamp: str
    prev_hash: str
    step_hash: str
    confidence: Optional[float] = None

class MultiLLMChain:
    """Orchestrates multiple LLM calls in sequence for robust clinical reasoning."""
    
    def __init__(self):
        self.chain_history: List[ChainStep] = []
        self.genesis_hash = "GENESIS_CHAIN"
    
    def _compute_step_hash(self, step_name: str, prompt: str, response: str, prev_hash: str) -> str:
        """Compute cryptographic hash for this chain step"""
        data = {"step": step_name, "prompt": prompt, "response": response, "prev_hash": prev_hash}
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def _get_last_hash(self) -> str:
        """Get hash of previous step in chain"""
        return self.chain_history[-1].step_hash if self.chain_history else self.genesis_hash
    
    def run_chain(self, patient_context: Dict, query: str, retrieved_evidence: List[Dict], bayesian_result: Dict) -> Dict:
        """Execute the full 4-LLM decision chain."""
        self.chain_history = []
        
        kinetics_result = self._run_kinetics_model(patient_context, query, retrieved_evidence, bayesian_result)
        adversarial_result = self._run_adversarial_model(patient_context, query, kinetics_result)
        literature_result = self._run_literature_model(patient_context, query, kinetics_result, adversarial_result)
        final_result = self._run_arbiter_model(patient_context, query, kinetics_result, adversarial_result, literature_result)
        
        return {
            "chain_steps": [{"step": s.step_name, "response": s.response, "hash": s.step_hash, "confidence": s.confidence} for s in self.chain_history],
            "final_recommendation": final_result["response"],
            "final_confidence": final_result["confidence"],
            "chain_hash": self.chain_history[-1].step_hash,
            "total_steps": len(self.chain_history)
        }
    
    def _run_kinetics_model(self, patient_context: Dict, query: str, evidence: List[Dict], bayesian: Dict) -> ChainStep:
        """LLM #1: Kinetics Model"""
        evidence_summary = "\n".join([f"- {case.get('summary', 'N/A')}" for case in evidence[:10]])
        
        prompt = f"""You are a clinical pharmacologist focused ONLY on pharmacokinetics.

PATIENT: Age: {patient_context.get('age')}, Gender: {patient_context.get('gender')}, Labs: {patient_context.get('labs', 'Not provided')}
QUESTION: {query}
BAYESIAN: {bayesian['prob_safe']:.1%} safe based on {bayesian['n_cases']} cases
CASES: {evidence_summary}

TASK: Provide ONLY pharmacokinetic calculation and dose recommendation. 2 sentences max."""

        response = grok_query(prompt, max_tokens=200)
        step = ChainStep("Kinetics Model", prompt, response, datetime.utcnow().isoformat() + "Z", self._get_last_hash(), "", bayesian['prob_safe'])
        step.step_hash = self._compute_step_hash(step.step_name, step.prompt, step.response, step.prev_hash)
        self.chain_history.append(step)
        return step
    
    def _run_adversarial_model(self, patient_context: Dict, query: str, kinetics_step: ChainStep) -> ChainStep:
        """LLM #2: Adversarial Model"""
        prompt = f"""You are a PARANOID anesthesiologist reviewing a colleague's recommendation.

PATIENT: {patient_context.get('age')}yo {patient_context.get('gender')}
QUESTION: {query}
COLLEAGUE'S REC: {kinetics_step.response}

TASK: Find ANY reason this could harm the patient. Focus on drug interactions, comorbidities, edge cases. 2-3 sentences."""

        response = grok_query(prompt, max_tokens=250)
        step = ChainStep("Adversarial Model", prompt, response, datetime.utcnow().isoformat() + "Z", self._get_last_hash(), "", None)
        step.step_hash = self._compute_step_hash(step.step_name, step.prompt, step.response, step.prev_hash)
        self.chain_history.append(step)
        return step
    
    def _run_literature_model(self, patient_context: Dict, query: str, kinetics_step: ChainStep, adversarial_step: ChainStep) -> ChainStep:
        """LLM #3: Literature Model"""
        prompt = f"""You are a clinical researcher with latest medical literature.

SCENARIO: {query}
PROPOSED: {kinetics_step.response}
RISKS: {adversarial_step.response}

TASK: Provide evidence from recent studies (2023-2025). What do trials suggest? Safer alternatives? 2-3 sentences."""

        response = grok_query(prompt, max_tokens=300)
        step = ChainStep("Literature Model", prompt, response, datetime.utcnow().isoformat() + "Z", self._get_last_hash(), "", 0.90)
        step.step_hash = self._compute_step_hash(step.step_name, step.prompt, step.response, step.prev_hash)
        self.chain_history.append(step)
        return step
    
    def _run_arbiter_model(self, patient_context: Dict, query: str, kinetics_step: ChainStep, adversarial_step: ChainStep, literature_step: ChainStep) -> Dict:
        """LLM #4: Arbiter Model"""
        prompt = f"""You are the attending making the FINAL decision.

PATIENT: {patient_context.get('age')}yo {patient_context.get('gender')}
QUESTION: {query}

INPUTS:
1. Pharmacologist: {kinetics_step.response}
2. Risk Analyst: {adversarial_step.response}
3. Researcher: {literature_step.response}

TASK: Synthesize into clear recommendation. Format: "Recommendation: [action] / Safety: [%] / Rationale: [why] / Monitor: [what]" 4 sentences max."""

        response = grok_query(prompt, max_tokens=300)
        final_confidence = (kinetics_step.confidence or 0.8) * 0.3 + 0.85 * 0.2 + (literature_step.confidence or 0.9) * 0.5
        
        step = ChainStep("Arbiter Model", prompt, response, datetime.utcnow().isoformat() + "Z", self._get_last_hash(), "", final_confidence)
        step.step_hash = self._compute_step_hash(step.step_name, step.prompt, step.response, step.prev_hash)
        self.chain_history.append(step)
        
        return {"step": step, "response": step.response, "confidence": final_confidence}
    
    def export_chain(self) -> Dict:
        """Export complete chain for audit"""
        return {
            "chain_id": self.chain_history[-1].step_hash if self.chain_history else None,
            "genesis_hash": self.genesis_hash,
            "steps": [{"step_name": s.step_name, "response": s.response, "timestamp": s.timestamp, "hash": s.step_hash, "prev_hash": s.prev_hash, "confidence": s.confidence} for s in self.chain_history],
            "total_steps": len(self.chain_history),
            "chain_verified": self.verify_chain()
        }
    
    def verify_chain(self) -> bool:
        """Verify cryptographic integrity"""
        if not self.chain_history:
            return True
        expected_prev_hash = self.genesis_hash
        for step in self.chain_history:
            if step.prev_hash != expected_prev_hash:
                return False
            computed_hash = self._compute_step_hash(step.step_name, step.prompt, step.response, step.prev_hash)
            if computed_hash != step.step_hash:
                return False
            expected_prev_hash = step.step_hash
        return True

def run_multi_llm_decision(patient_context: Dict, query: str, retrieved_cases: List[Dict], bayesian_result: Dict) -> Dict:
    """Run complete multi-LLM decision chain."""
    chain = MultiLLMChain()
    result = chain.run_chain(patient_context, query, retrieved_cases, bayesian_result)
    result["chain_export"] = chain.export_chain()
    return result
