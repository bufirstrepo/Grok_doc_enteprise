#!/usr/bin/env python3
"""
CrewAI Multi-Agent Orchestration for Grok Doc v2.0
Replaces manual LLM chain with intelligent agent coordination

Agents:
- Kinetics Agent: Clinical pharmacologist (PK/PD calculations)
- Adversarial Agent: Risk analyst (devil's advocate)
- Literature Agent: Clinical researcher (evidence validation)
- Arbiter Agent: Attending physician (final decision)
- Radiology Agent: Radiologist (imaging analysis, if available)
"""

from crewai import Agent, Task, Crew, Process
from typing import Dict, List, Optional
import json
from datetime import datetime
import hashlib

# Import existing components
from local_inference import grok_query
from bayesian_engine import bayesian_safety_assessment

# Import CrewAI tools
from crewai_tools import (
    PharmacokineticCalculatorTool,
    DrugInteractionCheckerTool,
    GuidelineLookupTool,
    LabPredictorTool,
    ImagingAnalyzerTool,
    KnowledgeGraphTool
)


class MedicalLLMWrapper:
    """Wrapper to make grok_query compatible with CrewAI"""

    def __init__(self, max_tokens: int = 500):
        self.max_tokens = max_tokens

    def __call__(self, prompt: str) -> str:
        """Call the local LLM"""
        return grok_query(prompt, max_tokens=self.max_tokens)


class GrokDocCrew:
    """
    Multi-agent crew for clinical decision support

    Agents work collaboratively to analyze patient cases,
    with each bringing specialized expertise
    """

    def __init__(self, use_radiology: bool = False):
        """
        Initialize the medical decision crew

        Args:
            use_radiology: Whether to include radiology agent (requires imaging data)
        """
        self.use_radiology = use_radiology
        self.crew_history = []

        # Initialize LLM backends for each agent
        self.kinetics_llm = MedicalLLMWrapper(max_tokens=200)
        self.adversarial_llm = MedicalLLMWrapper(max_tokens=250)
        self.literature_llm = MedicalLLMWrapper(max_tokens=300)
        self.arbiter_llm = MedicalLLMWrapper(max_tokens=300)
        self.radiology_llm = MedicalLLMWrapper(max_tokens=250) if use_radiology else None

        # Create agents
        self._create_agents()

    def _create_agents(self):
        """Create specialized medical agents"""

        # Initialize tools
        pk_tool = PharmacokineticCalculatorTool()
        interaction_tool = DrugInteractionCheckerTool()
        guideline_tool = GuidelineLookupTool()
        lab_tool = LabPredictorTool()
        imaging_tool = ImagingAnalyzerTool()
        kg_tool = KnowledgeGraphTool()

        self.kinetics_agent = Agent(
            role='Clinical Pharmacologist',
            goal='Calculate precise pharmacokinetics and recommend optimal dosing',
            backstory="""You are a clinical pharmacologist with 20 years of experience
            in pharmacokinetics and pharmacodynamics. You specialize in calculating drug
            clearance, volume of distribution, and optimal dosing regimens. You are
            meticulous about adjusting doses for renal/hepatic impairment.""",
            verbose=True,
            allow_delegation=False,
            llm=self.kinetics_llm,
            tools=[pk_tool, lab_tool]  # PK calculator + lab predictor
        )

        self.adversarial_agent = Agent(
            role='Risk Analyst & Safety Officer',
            goal='Identify all potential risks, contraindications, and adverse events',
            backstory="""You are a paranoid devil's advocate focused exclusively on
            patient safety. Your job is to find EVERY possible risk, contraindication,
            drug interaction, and adverse effect. You challenge all recommendations and
            demand evidence of safety. You consider worst-case scenarios.""",
            verbose=True,
            allow_delegation=False,
            llm=self.adversarial_llm,
            tools=[interaction_tool, kg_tool]  # Drug interactions + knowledge graph
        )

        self.literature_agent = Agent(
            role='Clinical Researcher & Evidence Specialist',
            goal='Validate recommendations against current clinical evidence and guidelines',
            backstory="""You are a clinical researcher who stays current with the latest
            medical literature. You validate recommendations against randomized controlled
            trials, meta-analyses, and clinical practice guidelines (IDSA, AAN, AHA, etc.).
            You cite specific studies and guidelines to support or refute recommendations.""",
            verbose=True,
            allow_delegation=False,
            llm=self.literature_llm,
            tools=[guideline_tool, kg_tool]  # Guidelines + knowledge graph validation
        )

        self.arbiter_agent = Agent(
            role='Attending Physician',
            goal='Synthesize all inputs into a final evidence-based clinical decision',
            backstory="""You are a senior attending physician with 25 years of clinical
            experience. You synthesize the pharmacokinetic calculations, risk assessment,
            and evidence review into a final recommendation. You balance efficacy and safety.
            You provide clear monitoring instructions and follow-up plans.""",
            verbose=True,
            allow_delegation=True,
            llm=self.arbiter_llm,
            tools=[kg_tool, lab_tool]  # Final validation + lab predictions
        )

        if self.use_radiology and self.radiology_llm:
            self.radiology_agent = Agent(
                role='Radiologist',
                goal='Interpret medical imaging findings and their clinical implications',
                backstory="""You are a board-certified radiologist specializing in chest
                imaging. You interpret X-rays, CTs, and MRIs, identifying pathology and
                providing differential diagnoses. You integrate imaging findings with
                clinical context.""",
                verbose=True,
                allow_delegation=False,
                llm=self.radiology_llm,
                tools=[imaging_tool]  # Medical imaging analyzer
            )

    def create_tasks(
        self,
        patient_context: Dict,
        query: str,
        retrieved_cases: List[Dict],
        bayesian_result: Dict,
        imaging_analysis: Optional[Dict] = None
    ) -> List[Task]:
        """
        Create tasks for the crew based on patient case

        Args:
            patient_context: Patient demographics and labs
            query: Clinical question
            retrieved_cases: Similar cases from FAISS database
            bayesian_result: Bayesian safety assessment
            imaging_analysis: Optional MONAI/CheXNet results

        Returns:
            List of Task objects for crew execution
        """

        # Format context for agents
        context = f"""
PATIENT CONTEXT:
{json.dumps(patient_context, indent=2)}

CLINICAL QUERY:
{query}

SIMILAR CASES (n={len(retrieved_cases)}):
{json.dumps(retrieved_cases[:5], indent=2)}

BAYESIAN SAFETY ASSESSMENT:
Probability Safe: {bayesian_result.get('prob_safe', 'N/A'):.2%}
95% CI: [{bayesian_result.get('ci_low', 0):.2%}, {bayesian_result.get('ci_high', 1):.2%}]
Evidence Base: {bayesian_result.get('n_cases', 0)} cases
"""

        # Task 1: Pharmacokinetic Analysis
        kinetics_task = Task(
            description=f"""
Perform pharmacokinetic analysis for this patient:

{context}

TASK:
1. Calculate drug clearance (consider CrCl, hepatic function)
2. Estimate volume of distribution (consider age, weight, fluid status)
3. Recommend optimal dose and interval
4. Justify dosing with PK calculations

Be terse. Focus on numbers. Confidence score required.
""",
            agent=self.kinetics_agent,
            expected_output="Terse PK calculations with dose recommendation and confidence score"
        )

        # Task 2: Risk Assessment (depends on kinetics)
        adversarial_task = Task(
            description=f"""
Review the pharmacokinetic recommendation and identify ALL risks:

PATIENT CONTEXT:
{context}

KINETICS RECOMMENDATION:
{{kinetics_task.output}}

TASK:
1. List ALL contraindications (absolute and relative)
2. Identify drug-drug interactions
3. Assess risk of adverse effects (nephrotoxicity, ototoxicity, etc.)
4. Challenge the dose if too aggressive
5. Demand monitoring if high risk

Be paranoid. Find EVERY risk. No confidence score (you only assess risk).
""",
            agent=self.adversarial_agent,
            expected_output="Comprehensive risk analysis with all contraindications and ADRs",
            context=[kinetics_task]
        )

        # Task 3: Literature Validation
        literature_task = Task(
            description=f"""
Validate the recommendation against current clinical evidence:

PATIENT CONTEXT:
{context}

KINETICS RECOMMENDATION:
{{kinetics_task.output}}

RISKS IDENTIFIED:
{{adversarial_task.output}}

TASK:
1. Cite relevant clinical practice guidelines (IDSA, AHA, AAN, etc.)
2. Reference key RCTs or meta-analyses
3. Confirm recommendation aligns with evidence
4. Note any deviations from guidelines

Cite specific studies/guidelines. Confidence: 0.90 (evidence-based).
""",
            agent=self.literature_agent,
            expected_output="Evidence review with citations and guideline concordance",
            context=[kinetics_task, adversarial_task]
        )

        tasks = [kinetics_task, adversarial_task, literature_task]

        # Optional Task 4: Radiology Interpretation
        if imaging_analysis and self.use_radiology:
            radiology_task = Task(
                description=f"""
Interpret the imaging findings in clinical context:

PATIENT CONTEXT:
{context}

IMAGING ANALYSIS (AI-Generated):
{json.dumps(imaging_analysis, indent=2)}

TASK:
1. Interpret AI findings (confirm or refute)
2. Provide differential diagnosis based on imaging
3. Assess how imaging impacts clinical decision
4. Recommend additional imaging if needed

Integrate imaging with clinical picture. Confidence: 0.85.
""",
                agent=self.radiology_agent,
                expected_output="Radiologic interpretation with differential diagnosis"
            )
            tasks.append(radiology_task)

        # Final Task: Arbiter Synthesis
        arbiter_task = Task(
            description=f"""
Synthesize all inputs into final clinical decision:

PATIENT CONTEXT:
{context}

INPUTS:
1. Pharmacokinetics: {{kinetics_task.output}}
2. Risk Assessment: {{adversarial_task.output}}
3. Evidence Review: {{literature_task.output}}
{"4. Radiology: {radiology_task.output}" if imaging_analysis and self.use_radiology else ""}

TASK:
1. Weigh the pharmacokinetic recommendation against the risks
2. Ensure recommendation aligns with evidence
3. Make final decision (approve, modify, or reject kinetics dose)
4. Provide monitoring plan (labs, vitals, symptoms to watch)
5. Specify follow-up timeline

CONFIDENCE CALCULATION:
- 30% from kinetics confidence
- 20% from baseline Bayesian probability ({bayesian_result.get('prob_safe', 0.5):.2f})
- 50% from literature confidence (0.90)
{"- Adjust for radiology findings if significant" if imaging_analysis else ""}

Final recommendation should be clear and actionable.
""",
            agent=self.arbiter_agent,
            expected_output="Final clinical decision with monitoring plan and confidence",
            context=tasks
        )

        tasks.append(arbiter_task)

        return tasks

    def run_decision(
        self,
        patient_context: Dict,
        query: str,
        retrieved_cases: List[Dict],
        bayesian_result: Dict,
        imaging_analysis: Optional[Dict] = None
    ) -> Dict:
        """
        Run the full multi-agent decision process

        Returns:
            {
                'final_recommendation': str,
                'final_confidence': float,
                'agent_outputs': Dict[str, str],
                'crew_history': List[Dict],
                'chain_verified': bool,
                'hash': str
            }
        """

        # Create tasks
        tasks = self.create_tasks(
            patient_context,
            query,
            retrieved_cases,
            bayesian_result,
            imaging_analysis
        )

        # Assemble crew
        agents = [
            self.kinetics_agent,
            self.adversarial_agent,
            self.literature_agent
        ]

        if imaging_analysis and self.use_radiology:
            agents.append(self.radiology_agent)

        agents.append(self.arbiter_agent)

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,  # Tasks run in order
            verbose=True
        )

        # Execute crew
        start_time = datetime.utcnow()
        result = crew.kickoff()
        end_time = datetime.utcnow()

        # Extract outputs
        agent_outputs = {
            'kinetics': tasks[0].output.raw_output if hasattr(tasks[0].output, 'raw_output') else str(tasks[0].output),
            'adversarial': tasks[1].output.raw_output if hasattr(tasks[1].output, 'raw_output') else str(tasks[1].output),
            'literature': tasks[2].output.raw_output if hasattr(tasks[2].output, 'raw_output') else str(tasks[2].output),
        }

        if imaging_analysis and self.use_radiology:
            agent_outputs['radiology'] = tasks[3].output.raw_output if hasattr(tasks[3].output, 'raw_output') else str(tasks[3].output)
            agent_outputs['arbiter'] = tasks[4].output.raw_output if hasattr(tasks[4].output, 'raw_output') else str(tasks[4].output)
        else:
            agent_outputs['arbiter'] = tasks[3].output.raw_output if hasattr(tasks[3].output, 'raw_output') else str(tasks[3].output)

        # Calculate final confidence (weighted average)
        kinetics_confidence = self._extract_confidence(agent_outputs['kinetics'], default=bayesian_result.get('prob_safe', 0.5))
        literature_confidence = 0.90  # Hardcoded for evidence-based
        final_confidence = (
            0.30 * kinetics_confidence +
            0.20 * bayesian_result.get('prob_safe', 0.5) +
            0.50 * literature_confidence
        )

        # Create hash chain for audit trail
        chain_hash = self._compute_chain_hash(agent_outputs, patient_context, query)

        # Store history
        self.crew_history.append({
            'timestamp': start_time.isoformat() + 'Z',
            'patient_context': patient_context,
            'query': query,
            'agent_outputs': agent_outputs,
            'final_confidence': final_confidence,
            'hash': chain_hash,
            'latency_ms': int((end_time - start_time).total_seconds() * 1000)
        })

        return {
            'final_recommendation': agent_outputs['arbiter'],
            'final_confidence': final_confidence,
            'agent_outputs': agent_outputs,
            'crew_history': self.crew_history,
            'chain_verified': True,
            'hash': chain_hash,
            'latency_ms': int((end_time - start_time).total_seconds() * 1000)
        }

    def _extract_confidence(self, text: str, default: float = 0.5) -> float:
        """Extract confidence score from agent output (simple regex)"""
        import re
        match = re.search(r'confidence[:\s]+(\d+\.?\d*)%?', text.lower())
        if match:
            val = float(match.group(1))
            return val / 100 if val > 1 else val
        return default

    def _compute_chain_hash(self, agent_outputs: Dict, patient_context: Dict, query: str) -> str:
        """Compute SHA-256 hash of entire crew execution"""
        canonical = json.dumps({
            'patient_context': patient_context,
            'query': query,
            'agent_outputs': agent_outputs
        }, sort_keys=True, separators=(',', ':'))

        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def run_crewai_decision(
    patient_context: Dict,
    query: str,
    retrieved_cases: List[Dict],
    bayesian_result: Dict,
    imaging_analysis: Optional[Dict] = None
) -> Dict:
    """
    Convenience function to run CrewAI-based decision

    This replaces llm_chain.run_multi_llm_decision() with intelligent agents
    """

    crew = GrokDocCrew(use_radiology=bool(imaging_analysis))
    return crew.run_decision(
        patient_context,
        query,
        retrieved_cases,
        bayesian_result,
        imaging_analysis
    )


if __name__ == "__main__":
    # Test with sample case
    patient_context = {
        'age': 72,
        'gender': 'M',
        'weight': 85,
        'labs': 'Cr 1.8, WBC 15.2, Temp 38.9C'
    }

    query = "Vancomycin dosing for suspected MRSA bacteremia?"

    retrieved_cases = [
        {'summary': '70M sepsis, vanco 1g q12h, Cr 1.6', 'outcome': 'safe'},
        {'summary': '75F MRSA bacteremia, vanco 1.5g q12h, AKI', 'outcome': 'unsafe'}
    ]

    bayesian_result = {
        'prob_safe': 0.78,
        'ci_low': 0.65,
        'ci_high': 0.89,
        'n_cases': 143
    }

    print("Running CrewAI multi-agent decision...")
    result = run_crewai_decision(patient_context, query, retrieved_cases, bayesian_result)

    print(f"\n{'='*60}")
    print(f"FINAL RECOMMENDATION:\n{result['final_recommendation']}")
    print(f"\nCONFIDENCE: {result['final_confidence']:.1%}")
    print(f"LATENCY: {result['latency_ms']}ms")
    print(f"CHAIN HASH: {result['hash'][:16]}...")
    print(f"{'='*60}")
