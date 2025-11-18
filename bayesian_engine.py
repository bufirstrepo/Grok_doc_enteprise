"""
Bayesian inference engine for clinical safety assessment.
Uses PyMC for probabilistic reasoning over retrieved case evidence.
"""

import numpy as np
from typing import List, Dict, Optional
import warnings

# Suppress PyMC warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def bayesian_safety_assessment(
    retrieved_cases: List[Dict],
    query_type: str = "general_safety",
    prior_alpha: float = 8.0,
    prior_beta: float = 2.0
) -> Dict:
    """
    Perform Bayesian safety assessment based on retrieved similar cases.
    
    Args:
        retrieved_cases: List of similar case dictionaries from vector search
        query_type: Type of safety query ("nephrotoxicity", "drug_interaction", "general_safety")
        prior_alpha: Beta distribution alpha (successes + 1)
        prior_beta: Beta distribution beta (failures + 1)
    
    Returns:
        Dict with probability estimates and credible intervals
    """
    
    if not retrieved_cases:
        return {
            "prob_safe": 0.5,
            "ci_low": 0.3,
            "ci_high": 0.7,
            "n_cases": 0,
            "n_safe": 0,
            "n_adverse": 0,
            "method": "default_prior"
        }
    
    # Extract safety outcomes from retrieved cases
    safety_outcomes = extract_safety_outcomes(retrieved_cases, query_type)
    
    n_safe = safety_outcomes["n_safe"]
    n_adverse = safety_outcomes["n_adverse"]
    n_total = n_safe + n_adverse
    
    # Bayesian update: Beta-Binomial conjugate prior
    # Prior: Beta(alpha, beta)
    # Likelihood: Binomial(n_safe | n_total, p)
    # Posterior: Beta(alpha + n_safe, beta + n_adverse)
    
    posterior_alpha = prior_alpha + n_safe
    posterior_beta = prior_beta + n_adverse
    
    # Mean of Beta distribution
    prob_safe = posterior_alpha / (posterior_alpha + posterior_beta)
    
    # 95% Credible interval using quantiles of Beta distribution
    from scipy.stats import beta as beta_dist
    ci_low, ci_high = beta_dist.ppf([0.025, 0.975], posterior_alpha, posterior_beta)
    
    return {
        "prob_safe": float(prob_safe),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "n_cases": n_total,
        "n_safe": n_safe,
        "n_adverse": n_adverse,
        "posterior_alpha": posterior_alpha,
        "posterior_beta": posterior_beta,
        "method": "beta_binomial"
    }

def bayesian_safety_assessment_mcmc(
    retrieved_cases: List[Dict],
    query_type: str = "general_safety",
    prior_alpha: float = 8.0,
    prior_beta: float = 2.0,
    n_samples: int = 2000,
    n_chains: int = 2
) -> Dict:
    """
    Full MCMC Bayesian inference using PyMC.
    More computationally intensive but provides richer uncertainty quantification.
    
    Args:
        retrieved_cases: List of similar case dictionaries
        query_type: Type of safety query
        prior_alpha: Beta prior alpha
        prior_beta: Beta prior beta
        n_samples: Number of MCMC samples
        n_chains: Number of MCMC chains
    
    Returns:
        Dict with posterior samples and diagnostics
    """
    
    try:
        import pymc as pm
        import arviz as az
        
        safety_outcomes = extract_safety_outcomes(retrieved_cases, query_type)
        n_safe = safety_outcomes["n_safe"]
        n_total = safety_outcomes["n_safe"] + safety_outcomes["n_adverse"]
        
        if n_total == 0:
            # Return prior if no data
            return bayesian_safety_assessment(retrieved_cases, query_type, prior_alpha, prior_beta)
        
        with pm.Model() as model:
            # Prior: Beta distribution for probability of safety
            p_safe = pm.Beta("p_safe", alpha=prior_alpha, beta=prior_beta)
            
            # Likelihood: Binomial distribution
            likelihood = pm.Binomial(
                "n_safe_obs",
                n=n_total,
                p=p_safe,
                observed=n_safe
            )
            
            # Sample from posterior
            trace = pm.sample(
                draws=n_samples,
                tune=1000,
                chains=n_chains,
                cores=1,
                progressbar=False,
                return_inferencedata=True
            )
        
        # Extract posterior statistics
        summary = az.summary(trace, var_names=["p_safe"])
        posterior_samples = trace.posterior["p_safe"].values.flatten()
        
        prob_safe = float(summary["mean"].iloc[0])
        ci_low, ci_high = np.percentile(posterior_samples, [2.5, 97.5])
        
        # Compute diagnostics
        rhat = float(summary["r_hat"].iloc[0]) if "r_hat" in summary.columns else 1.0
        ess = float(summary["ess_bulk"].iloc[0]) if "ess_bulk" in summary.columns else n_samples
        
        return {
            "prob_safe": prob_safe,
            "ci_low": float(ci_low),
            "ci_high": float(ci_high),
            "n_cases": n_total,
            "n_safe": n_safe,
            "n_adverse": safety_outcomes["n_adverse"],
            "method": "mcmc",
            "rhat": rhat,
            "ess": ess,
            "converged": rhat < 1.1
        }
        
    except ImportError:
        # Fall back to analytical solution if PyMC not available
        return bayesian_safety_assessment(retrieved_cases, query_type, prior_alpha, prior_beta)
    except Exception as e:
        print(f"MCMC failed: {e}, falling back to analytical solution")
        return bayesian_safety_assessment(retrieved_cases, query_type, prior_alpha, prior_beta)

def extract_safety_outcomes(cases: List[Dict], query_type: str) -> Dict:
    """
    Extract safety outcomes from retrieved cases based on query type.
    
    Args:
        cases: List of case dictionaries
        query_type: Type of safety concern
    
    Returns:
        Dict with counts of safe vs adverse outcomes
    """
    
    n_safe = 0
    n_adverse = 0
    
    for case in cases:
        outcome = classify_case_outcome(case, query_type)
        if outcome == "safe":
            n_safe += 1
        elif outcome == "adverse":
            n_adverse += 1
        # "unknown" cases are excluded from counts
    
    return {
        "n_safe": n_safe,
        "n_adverse": n_adverse
    }

def classify_case_outcome(case: Dict, query_type: str) -> str:
    """
    Classify a single case as safe, adverse, or unknown.
    
    Args:
        case: Case dictionary with outcome information
        query_type: Type of safety query
    
    Returns:
        "safe", "adverse", or "unknown"
    """
    
    # Check for explicit outcome field
    if "outcome" in case:
        outcome = case["outcome"].lower()
        if "safe" in outcome or "no adverse" in outcome or "recovered" in outcome:
            return "safe"
        elif "adverse" in outcome or "toxicity" in outcome or "complication" in outcome:
            return "adverse"
    
    # Check for query-specific flags
    if query_type == "nephrotoxicity":
        if case.get("nephrotoxicity", False) or case.get("aki", False):
            return "adverse"
        elif case.get("renal_function_stable", False):
            return "safe"
    
    elif query_type == "drug_interaction":
        if case.get("drug_interaction", False):
            return "adverse"
        elif case.get("no_interaction", False):
            return "safe"
    
    elif query_type == "general_safety":
        # Look for general safety indicators
        if case.get("adverse_event", False):
            return "adverse"
        elif case.get("safe", False) or case.get("no_complications", False):
            return "safe"
    
    # Check severity scores
    if "severity" in case:
        severity = case["severity"]
        if isinstance(severity, (int, float)):
            if severity <= 2:  # Mild
                return "safe"
            elif severity >= 4:  # Severe
                return "adverse"
    
    # Default to unknown if we can't classify
    return "unknown"

def compute_risk_score(bayesian_result: Dict) -> Dict:
    """
    Convert Bayesian probability to clinical risk categories.
    
    Args:
        bayesian_result: Output from bayesian_safety_assessment
    
    Returns:
        Dict with risk category and recommendation
    """
    
    prob_safe = bayesian_result["prob_safe"]
    ci_low = bayesian_result["ci_low"]
    
    # Use lower bound of credible interval for conservative estimate
    conservative_prob = ci_low
    
    if conservative_prob >= 0.95:
        risk_category = "Very Low Risk"
        recommendation = "Proceed with standard monitoring"
        color = "green"
    elif conservative_prob >= 0.85:
        risk_category = "Low Risk"
        recommendation = "Proceed with enhanced monitoring"
        color = "lightgreen"
    elif conservative_prob >= 0.70:
        risk_category = "Moderate Risk"
        recommendation = "Consider alternatives or intensive monitoring"
        color = "yellow"
    elif conservative_prob >= 0.50:
        risk_category = "High Risk"
        recommendation = "Recommend alternative approach"
        color = "orange"
    else:
        risk_category = "Very High Risk"
        recommendation = "Strongly recommend alternative approach"
        color = "red"
    
    return {
        "risk_category": risk_category,
        "recommendation": recommendation,
        "color": color,
        "prob_safe": prob_safe,
        "conservative_estimate": conservative_prob
    }

# Convenience function that combines everything
def full_bayesian_analysis(
    retrieved_cases: List[Dict],
    query_type: str = "general_safety",
    use_mcmc: bool = False
) -> Dict:
    """
    Complete Bayesian analysis with risk scoring.
    
    Args:
        retrieved_cases: Cases from vector search
        query_type: Type of safety analysis
        use_mcmc: Whether to use full MCMC (slower but more accurate)
    
    Returns:
        Combined results with Bayesian stats and risk assessment
    """
    
    if use_mcmc:
        bayesian_result = bayesian_safety_assessment_mcmc(retrieved_cases, query_type)
    else:
        bayesian_result = bayesian_safety_assessment(retrieved_cases, query_type)
    
    risk_assessment = compute_risk_score(bayesian_result)
    
    return {
        **bayesian_result,
        **risk_assessment
    }
