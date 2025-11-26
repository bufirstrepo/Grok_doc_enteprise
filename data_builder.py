"""
Build sample clinical case database for Grok Doc.
In production, replace with real de-identified case data.
"""

import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path

# Sample clinical cases (in production, load from hospital EHR)
SAMPLE_CASES = [
    {
        "id": "case_001",
        "summary": "72M with septic shock on vancomycin, Cr improved from 2.9 to 1.8, trough 15.2, continued safely",
        "outcome": "safe",
        "nephrotoxicity": False,
        "renal_function_stable": True,
        "severity": 2,
        "age": 72,
        "gender": "M",
        "drug": "vancomycin"
    },
    {
        "id": "case_002",
        "summary": "68F pneumonia on vancomycin, trough 22.1, developed AKI, drug discontinued",
        "outcome": "adverse - nephrotoxicity",
        "nephrotoxicity": True,
        "aki": True,
        "severity": 4,
        "age": 68,
        "gender": "F",
        "drug": "vancomycin"
    },
    {
        "id": "case_003",
        "summary": "55M with MRSA bacteremia, vancomycin trough 18.5, renal function remained stable throughout treatment",
        "outcome": "safe",
        "nephrotoxicity": False,
        "renal_function_stable": True,
        "severity": 1,
        "age": 55,
        "gender": "M",
        "drug": "vancomycin"
    },
    {
        "id": "case_004",
        "summary": "80F with UTI, vancomycin plus gentamicin, developed acute tubular necrosis",
        "outcome": "adverse - drug interaction nephrotoxicity",
        "nephrotoxicity": True,
        "drug_interaction": True,
        "severity": 5,
        "age": 80,
        "gender": "F",
        "drug": "vancomycin"
    },
    {
        "id": "case_005",
        "summary": "45M endocarditis, vancomycin for 6 weeks, trough 12-16 range, no complications",
        "outcome": "safe",
        "nephrotoxicity": False,
        "no_complications": True,
        "severity": 1,
        "age": 45,
        "gender": "M",
        "drug": "vancomycin"
    },
    {
        "id": "case_006",
        "summary": "70F sepsis, ceftriaxone empiric therapy, defervesced in 48h, completed course without issues",
        "outcome": "safe",
        "no_complications": True,
        "severity": 1,
        "age": 70,
        "gender": "F",
        "drug": "ceftriaxone"
    },
    {
        "id": "case_007",
        "summary": "62M pneumonia on piperacillin-tazobactam, developed C. diff colitis day 5",
        "outcome": "adverse - antibiotic-associated colitis",
        "adverse_event": True,
        "severity": 4,
        "age": 62,
        "gender": "M",
        "drug": "piperacillin-tazobactam"
    },
    {
        "id": "case_008",
        "summary": "75M ventilator-associated pneumonia, meropenem therapy, clinical improvement, extubated day 7",
        "outcome": "safe",
        "no_complications": True,
        "severity": 2,
        "age": 75,
        "gender": "M",
        "drug": "meropenem"
    },
    {
        "id": "case_009",
        "summary": "58F with severe sepsis, norepinephrine requirement decreased after 72h of appropriate antibiotics",
        "outcome": "safe",
        "severity": 2,
        "age": 58,
        "gender": "F"
    },
    {
        "id": "case_010",
        "summary": "81M with acute renal failure on vancomycin, trough 28.3, dialysis required, drug stopped",
        "outcome": "adverse - severe nephrotoxicity",
        "nephrotoxicity": True,
        "aki": True,
        "severity": 5,
        "age": 81,
        "gender": "M",
        "drug": "vancomycin"
    },
    # Add more diverse cases
    {
        "id": "case_011",
        "summary": "66M diabetic foot infection, vancomycin therapy with stable glucose control and wound healing",
        "outcome": "safe",
        "nephrotoxicity": False,
        "no_complications": True,
        "severity": 2,
        "age": 66,
        "gender": "M",
        "drug": "vancomycin"
    },
    {
        "id": "case_012",
        "summary": "52F osteomyelitis on long-term vancomycin, weekly monitoring, no adverse effects over 8 weeks",
        "outcome": "safe",
        "nephrotoxicity": False,
        "renal_function_stable": True,
        "severity": 1,
        "age": 52,
        "gender": "F",
        "drug": "vancomycin"
    },
    {
        "id": "case_013",
        "summary": "77M hospital-acquired pneumonia, vancomycin plus cefepime, acute interstitial nephritis developed",
        "outcome": "adverse - drug-induced nephritis",
        "nephrotoxicity": True,
        "drug_interaction": True,
        "severity": 4,
        "age": 77,
        "gender": "M",
        "drug": "vancomycin"
    },
    {
        "id": "case_014",
        "summary": "43M with normal renal function, vancomycin trough 14.8, completed treatment without issues",
        "outcome": "safe",
        "nephrotoxicity": False,
        "renal_function_stable": True,
        "severity": 1,
        "age": 43,
        "gender": "M",
        "drug": "vancomycin"
    },
    {
        "id": "case_015",
        "summary": "69F bloodstream infection, vancomycin + piperacillin-tazobactam, cleared infection, renal function normal",
        "outcome": "safe",
        "nephrotoxicity": False,
        "no_complications": True,
        "severity": 2,
        "age": 69,
        "gender": "F",
        "drug": "vancomycin"
    }
]

def generate_synthetic_cases(n_cases: int = 17000) -> list:
    """
    Generate synthetic clinical cases by augmenting base cases.
    In production, replace with real de-identified hospital data.
    
    Args:
        n_cases: Number of synthetic cases to generate
    
    Returns:
        List of case dictionaries
    """
    
    synthetic_cases = []
    
    # Start with real sample cases
    synthetic_cases.extend(SAMPLE_CASES)
    
    # Drug categories for variation
    antibiotics = [
        "vancomycin", "ceftriaxone", "piperacillin-tazobactam", 
        "meropenem", "azithromycin", "ciprofloxacin", "linezolid",
        "daptomycin", "cefepime", "ampicillin-sulbactam"
    ]
    
    conditions = [
        "septic shock", "pneumonia", "UTI", "bacteremia", "endocarditis",
        "osteomyelitis", "cellulitis", "meningitis", "intra-abdominal infection",
        "surgical site infection"
    ]
    
    # Generate additional cases
    for i in range(len(SAMPLE_CASES), n_cases):
        age = np.random.randint(18, 95)
        gender = np.random.choice(["M", "F"])
        drug = np.random.choice(antibiotics)
        condition = np.random.choice(conditions)
        
        # 85% safe, 15% adverse (realistic distribution)
        is_adverse = np.random.random() < 0.15
        
        if is_adverse:
            outcomes = [
                f"{age}{gender} with {condition} on {drug}, developed nephrotoxicity",
                f"{age}{gender} {condition}, {drug} therapy complicated by AKI",
                f"{age}{gender} on {drug} for {condition}, adverse drug reaction requiring discontinuation"
            ]
            outcome_label = "adverse"
            nephrotoxicity = drug in ["vancomycin", "gentamicin", "amphotericin"] and np.random.random() < 0.7
            severity = np.random.randint(3, 6)
        else:
            outcomes = [
                f"{age}{gender} with {condition} on {drug}, completed treatment successfully",
                f"{age}{gender} {condition}, {drug} therapy with good response and no complications",
                f"{age}{gender} on {drug} for {condition}, stable renal function throughout treatment"
            ]
            outcome_label = "safe"
            nephrotoxicity = False
            severity = np.random.randint(1, 3)
        
        summary = np.random.choice(outcomes)
        
        case = {
            "id": f"case_{i:06d}",
            "summary": summary,
            "outcome": outcome_label,
            "nephrotoxicity": nephrotoxicity,
            "renal_function_stable": not is_adverse,
            "severity": severity,
            "age": age,
            "gender": gender,
            "drug": drug,
            "condition": condition,
            "adverse_event": is_adverse
        }
        
        synthetic_cases.append(case)
    
    return synthetic_cases

def create_sample_database(embedder: SentenceTransformer, n_cases: int = 17000):
    """
    Create FAISS index and JSONL database from sample cases.
    
    Args:
        embedder: Sentence transformer model for embeddings
        n_cases: Number of cases to generate
    """
    
    print(f"Generating {n_cases} synthetic clinical cases...")
    cases = generate_synthetic_cases(n_cases)
    
    print("Creating embeddings...")
    # Extract summaries for embedding
    summaries = [case["summary"] for case in cases]
    
    # Generate embeddings in batches for efficiency
    batch_size = 256
    all_embeddings = []
    
    for i in range(0, len(summaries), batch_size):
        batch = summaries[i:i+batch_size]
        embeddings = embedder.encode(batch, show_progress_bar=False)
        all_embeddings.append(embeddings)
        
        if (i // batch_size) % 10 == 0:
            print(f"  Processed {i}/{len(summaries)} cases...")
    
    embeddings = np.vstack(all_embeddings).astype('float32')
    
    print("Building FAISS index...")
    # Create FAISS index (L2 distance)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save index
    index_path = "case_index.faiss"
    faiss.write_index(index, index_path)
    print(f"✓ Saved FAISS index to {index_path}")
    
    # Save cases as JSONL
    cases_path = "cases_17k.jsonl"
    with open(cases_path, 'w') as f:
        for case in cases:
            f.write(json.dumps(case) + '\n')
    print(f"✓ Saved {len(cases)} cases to {cases_path}")
    
    print(f"\n✓ Database creation complete!")
    print(f"  - {len(cases)} clinical cases")
    print(f"  - {dimension}-dimensional embeddings")
    print(f"  - Index size: {Path(index_path).stat().st_size / 1e6:.1f} MB")
    print(f"  - Cases size: {Path(cases_path).stat().st_size / 1e6:.1f} MB")

def verify_database():
    """
    Verify that the database was created correctly.
    """
    try:
        # Check files exist
        assert Path("case_index.faiss").exists(), "FAISS index not found"
        assert Path("cases_17k.jsonl").exists(), "Cases file not found"
        
        # Load and verify index
        index = faiss.read_index("case_index.faiss")
        print(f"✓ FAISS index loaded: {index.ntotal} vectors")
        
        # Load and verify cases
        with open("cases_17k.jsonl", 'r') as f:
            cases = [json.loads(line) for line in f]
        print(f"✓ Cases loaded: {len(cases)} entries")
        
        # Verify counts match
        assert index.ntotal == len(cases), "Mismatch between index and cases count"
        
        # Check case structure
        sample_case = cases[0]
        required_fields = ["id", "summary", "outcome"]
        for field in required_fields:
            assert field in sample_case, f"Missing required field: {field}"
        
        print("✓ Database verification passed!")
        return True
        
    except Exception as e:
        print(f"✗ Database verification failed: {e}")
        return False

if __name__ == "__main__":
    # Build database if run directly
    from sentence_transformers import SentenceTransformer
    
    print("Loading embedding model...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    create_sample_database(embedder, n_cases=17000)
    verify_database()
