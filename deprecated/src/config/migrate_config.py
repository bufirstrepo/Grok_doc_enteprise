import json
import os
import shutil
from datetime import datetime

OLD_CONFIG_PATH = "config/hospital_config.json"
NEW_CONFIG_PATH = "config/hospital_config.json"
BACKUP_PATH = f"config/hospital_config_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"

def migrate():
    if not os.path.exists(OLD_CONFIG_PATH):
        print(f"No config found at {OLD_CONFIG_PATH}")
        return

    print(f"Backing up config to {BACKUP_PATH}")
    shutil.copy(OLD_CONFIG_PATH, BACKUP_PATH)

    with open(OLD_CONFIG_PATH, 'r') as f:
        old_data = json.load(f)

    print("Migrating to v3.1 Schema...")
    
    # Create new structure
    new_data = {
        "hospital_name": old_data.get("hospital_name", "Unknown Hospital"),
        "site_id": old_data.get("site_id", "SITE-001"),
        "ehr": old_data.get("ehr", {
            "system": "Other",
            "fhir_url": "http://localhost:8080/fhir",
            "client_id": "mock_client"
        }),
        "ai_tools": old_data.get("ai_tools", {}),
        "features": old_data.get("features", {}),
        "compliance": old_data.get("compliance", {}),
        "llm_config": old_data.get("llm_config", {
            "default_model": "grok-beta",
            "chain_mode_enabled": True,
            "fast_mode_enabled": True
        })
    }

    # Normalize AI Tools
    # Ensure all tools have 'backend' and 'enabled'
    for model, tool in new_data["ai_tools"].items():
        if "backend" not in tool:
            tool["backend"] = "xai_api" # Default
        if "enabled" not in tool:
            tool["enabled"] = True

    # Add new v3.1 fields if missing
    if "ldap_enabled" not in new_data["compliance"]:
        new_data["compliance"]["ldap_enabled"] = False
        new_data["compliance"]["ldap_server"] = "ldap://localhost"

    if "encryption_enabled" not in new_data["compliance"]:
        new_data["compliance"]["encryption_enabled"] = True

    with open(NEW_CONFIG_PATH, 'w') as f:
        json.dump(new_data, f, indent=2)

    print("Migration Complete!")
    print(f"New config saved to {NEW_CONFIG_PATH}")

if __name__ == "__main__":
    migrate()
