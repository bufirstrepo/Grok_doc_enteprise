from prompt_personas import get_updated_personas
import json

def verify():
    print("Loading personas...")
    personas = get_updated_personas()
    
    cyber_persona = None
    for p in personas['red_team']:
        if "Cybersecurity Safety Officer" in p:
            cyber_persona = p
            break
            
    if cyber_persona:
        print("\nFOUND CYBERSECURITY PERSONA:")
        print("-" * 40)
        print(cyber_persona)
        print("-" * 40)
        
        # Verify dynamic year
        import datetime
        current_year = datetime.datetime.now().year
        if str(current_year) in cyber_persona:
             print(f"\n[PASS] Dynamic year {current_year} found.")
        else:
             print(f"\n[FAIL] Dynamic year {current_year} NOT found.")

        # Verify specific phrases from user request
        checks = [
            "BLAKE3-chained",
            "Anomaly score >0.87",
            "CVSS ≥9.0",
            "SHAP/LIME explainability",
            "Human–System Trust Collapse Risk"
        ]
        
        all_pass = True
        for check in checks:
            if check in cyber_persona:
                print(f"[PASS] Found phrase: '{check}'")
            else:
                print(f"[FAIL] Missing phrase: '{check}'")
                all_pass = False
                
        if all_pass:
            print("\n[SUCCESS] All checks passed.")
        else:
            print("\n[FAILURE] Some checks failed.")
            
    else:
        print("\n[FAIL] Cybersecurity persona NOT found in 'red_team' list.")

if __name__ == "__main__":
    verify()
