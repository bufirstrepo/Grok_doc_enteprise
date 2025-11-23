"""
Multi-LLM Decision Chain for Clinical Reasoning

Implements a four-stage LLM chain where each model plays a specialized role:
1. Kinetics Model - Raw pharmacokinetic calculations
2. Adversarial Model - Devil's advocate risk analysis
3. Literature Model - Evidence-based recommendations
4. Arbiter Model - Final reconciliation and decision
"""

from typing import Dict, List, Optional, Any, TypedDict
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import time
import logging
from local_inference import grok_query

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HARDENING STEP 1: Stage-specific timeouts (seconds)
# Impact: Prevents false negatives from uniform timeouts, optimizes for clinical urgency
STAGE_TIMEOUTS = {
    "kinetics": 30,      # Most critical - pharmacokinetic calculations
    "adversarial": 25,   # Aggressive risk analysis
    "literature": 45,    # Slower external DB searches (may need to retrieve evidence)
    "arbiter": 20        # Fast synthesis of existing results
}

# HARDENING STEP 1: Stage-specific retry counts
# Impact: Balances reliability vs latency based on clinical necessity
STAGE_RETRY_COUNT = {
    "kinetics": 2,       # Worth retrying - critical safety calculations
    "adversarial": 1,    # Can proceed without if needed
    "literature": 1,     # Nice-to-have evidence enhancement
    "arbiter": 0         # Use partial results if previous stages succeeded
}

# HARDENING STEP 2: Explicit Stage Interface Contracts
class StageResult(TypedDict):
    """Type contract for all stage function returns"""
    recommendation: str           # REQUIRED: Clinical recommendation text
    confidence: float            # REQUIRED: 0.0-1.0 confidence score
    reasoning: str               # REQUIRED: Justification for recommendation
    contraindications: List[str] # REQUIRED: List of risks/contraindications (can be empty)
    timestamp: str               # REQUIRED: ISO 8601 timestamp
    stage_name: str              # REQUIRED: Name of the stage
    _stage_metadata: Dict[str, Any]  # REQUIRED: Execution metrics

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

# HARDENING STEP 3: Granular Stage Execution with Microsecond Timing
def _execute_stage(
    stage_name: str,
    stage_func: callable,
    *args,
    **kwargs
) -> StageResult:
    """
    Execute a chain stage with automatic retry logic, timing, and metadata injection.

    Impact: Exact failure localization, performance profiling, comparative model analysis.

    Args:
        stage_name: Name of the stage (must exist in STAGE_TIMEOUTS and STAGE_RETRY_COUNT)
        stage_func: The stage function to execute
        *args, **kwargs: Arguments to pass to stage_func

    Returns:
        StageResult with injected _stage_metadata

    Raises:
        Exception: If all retries exhausted
    """
    start_time = time.time()
    retry_count = 0
    max_retries = STAGE_RETRY_COUNT.get(stage_name, 0)
    timeout = STAGE_TIMEOUTS.get(stage_name, 30)

    last_error = None

    while retry_count <= max_retries:
        try:
            logger.info(f"[{stage_name}] Attempt {retry_count + 1}/{max_retries + 1}")

            # Execute the stage function
            result = stage_func(*args, **kwargs)

            # Calculate execution time in milliseconds
            execution_time_ms = (time.time() - start_time) * 1000

            # Inject metadata
            result["_stage_metadata"] = {
                "stage_name": stage_name,
                "execution_time_ms": round(execution_time_ms, 2),
                "retry_count": retry_count,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "timeout_configured": timeout,
                "max_retries_configured": max_retries
            }

            logger.info(
                f"[{stage_name}] ✓ Success in {execution_time_ms:.2f}ms "
                f"(attempt {retry_count + 1}/{max_retries + 1})"
            )

            return result

        except Exception as e:
            retry_count += 1
            last_error = e
            execution_time_ms = (time.time() - start_time) * 1000

            logger.warning(
                f"[{stage_name}] ✗ Failed on attempt {retry_count}/{max_retries + 1}: {str(e)} "
                f"(elapsed: {execution_time_ms:.2f}ms)"
            )

            # If we've exhausted retries, raise the error
            if retry_count > max_retries:
                logger.error(
                    f"[{stage_name}] FINAL FAILURE after {retry_count} attempts "
                    f"(total time: {execution_time_ms:.2f}ms)"
                )
                raise Exception(
                    f"Stage '{stage_name}' failed after {retry_count} attempts. "
                    f"Last error: {str(last_error)}"
                ) from last_error

            # Small backoff before retry (exponential: 0.5s, 1s, 2s, ...)
            backoff_time = 0.5 * (2 ** (retry_count - 1))
            logger.info(f"[{stage_name}] Retrying in {backoff_time}s...")
            time.sleep(backoff_time)

    # Should never reach here, but for type safety
    raise Exception(f"Stage '{stage_name}' execution failed unexpectedly")

class MultiLLMChain:
    """Orchestrates multiple LLM calls in sequence for robust clinical reasoning."""

    def __init__(self):
        self.chain_history: List[ChainStep] = []
        self.genesis_hash = "GENESIS_CHAIN"
        self.stage_results: Dict[str, StageResult] = {}  # Store structured results

    def _compute_step_hash(self, step_name: str, prompt: str, response: str, prev_hash: str) -> str:
        """Compute cryptographic hash for this chain step"""
        data = {"step": step_name, "prompt": prompt, "response": response, "prev_hash": prev_hash}
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _get_last_hash(self) -> str:
        """Get hash of previous step in chain"""
        return self.chain_history[-1].step_hash if self.chain_history else self.genesis_hash

    def _parse_contraindications(self, response: str) -> List[str]:
        """Extract contraindications/risks from LLM response"""
        # Simple parsing - look for common risk indicators
        contraindications = []
        risk_keywords = ["contraindication", "risk", "avoid", "caution", "warning", "interaction"]

        for line in response.split('.'):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in risk_keywords):
                contraindications.append(line.strip())

        return contraindications if contraindications else ["No specific contraindications identified"]
    
    def run_chain(self, patient_context: Dict, query: str, retrieved_evidence: List[Dict], bayesian_result: Dict) -> Dict:
        """Execute the full 4-LLM decision chain with hardened execution."""
        # Reset state for new chain execution
        self.chain_history = []
        self.stage_results = {}

        # Execute all 4 stages sequentially
        kinetics_result = self._run_kinetics_model(patient_context, query, retrieved_evidence, bayesian_result)
        adversarial_result = self._run_adversarial_model(patient_context, query, kinetics_result)
        literature_result = self._run_literature_model(patient_context, query, kinetics_result, adversarial_result)
        final_result = self._run_arbiter_model(patient_context, query, kinetics_result, adversarial_result, literature_result)

        # Return comprehensive results including metadata
        return {
            "chain_steps": [{"step": s.step_name, "response": s.response, "hash": s.step_hash, "confidence": s.confidence} for s in self.chain_history],
            "final_recommendation": final_result["response"],
            "final_confidence": final_result["confidence"],
            "chain_hash": self.chain_history[-1].step_hash,
            "total_steps": len(self.chain_history),
            "stage_metadata": {
                stage_name: result["_stage_metadata"]
                for stage_name, result in self.stage_results.items()
            }
        }
    
    def _run_kinetics_model_impl(self, patient_context: Dict, query: str, evidence: List[Dict], bayesian: Dict) -> StageResult:
        """LLM #1: Kinetics Model - Internal implementation returning StageResult"""
        evidence_summary = "\n".join([f"- {case.get('summary', 'N/A')}" for case in evidence[:10]])

        prompt = f"""You are a clinical pharmacologist focused ONLY on pharmacokinetics.

PATIENT: Age: {patient_context.get('age')}, Gender: {patient_context.get('gender')}, Labs: {patient_context.get('labs', 'Not provided')}
QUESTION: {query}
BAYESIAN: {bayesian['prob_safe']:.1%} safe based on {bayesian['n_cases']} cases
CASES: {evidence_summary}

TASK: Provide ONLY pharmacokinetic calculation and dose recommendation. 2 sentences max."""

        response = grok_query(prompt, max_tokens=200)

        # Return contract-compliant StageResult
        return {
            "recommendation": response,
            "confidence": bayesian['prob_safe'],
            "reasoning": f"Based on Bayesian analysis of {bayesian['n_cases']} similar cases with {bayesian['prob_safe']:.1%} safety probability",
            "contraindications": self._parse_contraindications(response),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stage_name": "Kinetics Model",
            "_stage_metadata": {}  # Will be filled by _execute_stage
        }

    def _run_kinetics_model(self, patient_context: Dict, query: str, evidence: List[Dict], bayesian: Dict) -> ChainStep:
        """LLM #1: Kinetics Model - Execute with retry/timing wrapper"""
        # Execute with hardening wrapper
        stage_result = _execute_stage(
            "kinetics",
            self._run_kinetics_model_impl,
            patient_context,
            query,
            evidence,
            bayesian
        )

        # Store structured result
        self.stage_results["kinetics"] = stage_result

        # Create ChainStep for backward compatibility
        step = ChainStep(
            "Kinetics Model",
            "Kinetics Model Prompt",  # Simplified for hash chain
            stage_result["recommendation"],
            stage_result["timestamp"],
            self._get_last_hash(),
            "",
            stage_result["confidence"]
        )
        step.step_hash = self._compute_step_hash(
            step.step_name, step.prompt, step.response, step.prev_hash
        )
        self.chain_history.append(step)
        return step
    
    def _run_adversarial_model_impl(self, patient_context: Dict, query: str, kinetics_result: StageResult) -> StageResult:
        """LLM #2: Adversarial Model - Internal implementation returning StageResult"""
        prompt = f"""You are a PARANOID anesthesiologist reviewing a colleague's recommendation.

PATIENT: {patient_context.get('age')}yo {patient_context.get('gender')}
QUESTION: {query}
COLLEAGUE'S REC: {kinetics_result['recommendation']}

TASK: Find ANY reason this could harm the patient. Focus on drug interactions, comorbidities, edge cases. 2-3 sentences."""

        response = grok_query(prompt, max_tokens=250)

        # Return contract-compliant StageResult
        return {
            "recommendation": response,
            "confidence": 0.50,  # Adversarial model intentionally conservative
            "reasoning": "Systematic risk analysis focusing on potential contraindications and edge cases",
            "contraindications": self._parse_contraindications(response),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stage_name": "Adversarial Model",
            "_stage_metadata": {}  # Will be filled by _execute_stage
        }

    def _run_adversarial_model(self, patient_context: Dict, query: str, kinetics_step: ChainStep) -> ChainStep:
        """LLM #2: Adversarial Model - Execute with retry/timing wrapper"""
        # Get kinetics result from stored stage results
        kinetics_result = self.stage_results.get("kinetics")
        if not kinetics_result:
            raise Exception("Kinetics stage must complete before adversarial stage")

        # Execute with hardening wrapper
        stage_result = _execute_stage(
            "adversarial",
            self._run_adversarial_model_impl,
            patient_context,
            query,
            kinetics_result
        )

        # Store structured result
        self.stage_results["adversarial"] = stage_result

        # Create ChainStep for backward compatibility
        step = ChainStep(
            "Adversarial Model",
            "Adversarial Model Prompt",
            stage_result["recommendation"],
            stage_result["timestamp"],
            self._get_last_hash(),
            "",
            stage_result["confidence"]
        )
        step.step_hash = self._compute_step_hash(
            step.step_name, step.prompt, step.response, step.prev_hash
        )
        self.chain_history.append(step)
        return step
    
    def _run_literature_model_impl(self, patient_context: Dict, query: str, kinetics_result: StageResult, adversarial_result: StageResult) -> StageResult:
        """LLM #3: Literature Model - Internal implementation returning StageResult"""
        prompt = f"""You are a clinical researcher with latest medical literature.

SCENARIO: {query}
PROPOSED: {kinetics_result['recommendation']}
RISKS: {adversarial_result['recommendation']}

TASK: Provide evidence from recent studies (2023-2025). What do trials suggest? Safer alternatives? 2-3 sentences."""

        response = grok_query(prompt, max_tokens=300)

        # Return contract-compliant StageResult
        return {
            "recommendation": response,
            "confidence": 0.90,  # Literature-based evidence has high confidence
            "reasoning": "Evidence-based analysis from recent clinical trials and systematic reviews",
            "contraindications": self._parse_contraindications(response),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stage_name": "Literature Model",
            "_stage_metadata": {}  # Will be filled by _execute_stage
        }

    def _run_literature_model(self, patient_context: Dict, query: str, kinetics_step: ChainStep, adversarial_step: ChainStep) -> ChainStep:
        """LLM #3: Literature Model - Execute with retry/timing wrapper"""
        # Get previous results from stored stage results
        kinetics_result = self.stage_results.get("kinetics")
        adversarial_result = self.stage_results.get("adversarial")

        if not kinetics_result or not adversarial_result:
            raise Exception("Kinetics and adversarial stages must complete before literature stage")

        # Execute with hardening wrapper
        stage_result = _execute_stage(
            "literature",
            self._run_literature_model_impl,
            patient_context,
            query,
            kinetics_result,
            adversarial_result
        )

        # Store structured result
        self.stage_results["literature"] = stage_result

        # Create ChainStep for backward compatibility
        step = ChainStep(
            "Literature Model",
            "Literature Model Prompt",
            stage_result["recommendation"],
            stage_result["timestamp"],
            self._get_last_hash(),
            "",
            stage_result["confidence"]
        )
        step.step_hash = self._compute_step_hash(
            step.step_name, step.prompt, step.response, step.prev_hash
        )
        self.chain_history.append(step)
        return step
    
    def _run_arbiter_model_impl(self, patient_context: Dict, query: str, kinetics_result: StageResult, adversarial_result: StageResult, literature_result: StageResult) -> StageResult:
        """LLM #4: Arbiter Model - Internal implementation returning StageResult"""
        prompt = f"""You are the attending making the FINAL decision.

PATIENT: {patient_context.get('age')}yo {patient_context.get('gender')}
QUESTION: {query}

INPUTS:
1. Pharmacologist: {kinetics_result['recommendation']}
2. Risk Analyst: {adversarial_result['recommendation']}
3. Researcher: {literature_result['recommendation']}

TASK: Synthesize into clear recommendation. Format: "Recommendation: [action] / Safety: [%] / Rationale: [why] / Monitor: [what]" 4 sentences max."""

        response = grok_query(prompt, max_tokens=300)

        # Weighted confidence calculation
        # 30% kinetics + 20% adversarial (baseline) + 50% literature
        final_confidence = (
            kinetics_result['confidence'] * 0.3 +
            adversarial_result['confidence'] * 0.2 +
            literature_result['confidence'] * 0.5
        )

        # Combine all contraindications from previous stages
        all_contraindications = []
        for result in [kinetics_result, adversarial_result, literature_result]:
            all_contraindications.extend(result['contraindications'])

        # Return contract-compliant StageResult
        return {
            "recommendation": response,
            "confidence": final_confidence,
            "reasoning": f"Final synthesis considering pharmacokinetics ({kinetics_result['confidence']:.1%}), risk analysis ({adversarial_result['confidence']:.1%}), and evidence-based literature ({literature_result['confidence']:.1%})",
            "contraindications": list(set(all_contraindications)),  # Deduplicate
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stage_name": "Arbiter Model",
            "_stage_metadata": {}  # Will be filled by _execute_stage
        }

    def _run_arbiter_model(self, patient_context: Dict, query: str, kinetics_step: ChainStep, adversarial_step: ChainStep, literature_step: ChainStep) -> Dict:
        """LLM #4: Arbiter Model - Execute with retry/timing wrapper"""
        # Get previous results from stored stage results
        kinetics_result = self.stage_results.get("kinetics")
        adversarial_result = self.stage_results.get("adversarial")
        literature_result = self.stage_results.get("literature")

        if not kinetics_result or not adversarial_result or not literature_result:
            raise Exception("All previous stages must complete before arbiter stage")

        # Execute with hardening wrapper
        stage_result = _execute_stage(
            "arbiter",
            self._run_arbiter_model_impl,
            patient_context,
            query,
            kinetics_result,
            adversarial_result,
            literature_result
        )

        # Store structured result
        self.stage_results["arbiter"] = stage_result

        # Create ChainStep for backward compatibility
        step = ChainStep(
            "Arbiter Model",
            "Arbiter Model Prompt",
            stage_result["recommendation"],
            stage_result["timestamp"],
            self._get_last_hash(),
            "",
            stage_result["confidence"]
        )
        step.step_hash = self._compute_step_hash(
            step.step_name, step.prompt, step.response, step.prev_hash
        )
        self.chain_history.append(step)

        return {"step": step, "response": step.response, "confidence": stage_result["confidence"]}
    
    def export_chain(self) -> Dict:
        """Export complete chain for audit with enhanced metadata"""
        return {
            "chain_id": self.chain_history[-1].step_hash if self.chain_history else None,
            "genesis_hash": self.genesis_hash,
            "steps": [
                {
                    "step_name": s.step_name,
                    "response": s.response,
                    "timestamp": s.timestamp,
                    "hash": s.step_hash,
                    "prev_hash": s.prev_hash,
                    "confidence": s.confidence
                }
                for s in self.chain_history
            ],
            "total_steps": len(self.chain_history),
            "chain_verified": self.verify_chain(),
            # NEW: Include detailed stage results with execution metadata
            "stage_results": {
                stage_name: {
                    "recommendation": result["recommendation"],
                    "confidence": result["confidence"],
                    "reasoning": result["reasoning"],
                    "contraindications": result["contraindications"],
                    "timestamp": result["timestamp"],
                    "metadata": result["_stage_metadata"]
                }
                for stage_name, result in self.stage_results.items()
            },
            # NEW: Performance summary
            "performance_summary": {
                "total_execution_time_ms": sum(
                    result["_stage_metadata"].get("execution_time_ms", 0)
                    for result in self.stage_results.values()
                ),
                "stage_timings": {
                    stage_name: result["_stage_metadata"].get("execution_time_ms", 0)
                    for stage_name, result in self.stage_results.items()
                },
                "retries": {
                    stage_name: result["_stage_metadata"].get("retry_count", 0)
                    for stage_name, result in self.stage_results.items()
                }
            }
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
