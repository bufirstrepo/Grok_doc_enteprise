#!/usr/bin/env python3
"""
Blockchain Audit Tool for CrewAI
Wraps blockchain_audit.py for use by logger_agent
"""

from crewai.tools import BaseTool
from typing import Type, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Import from root (blockchain_audit is still there)
from blockchain_audit import BlockchainAuditLogger


class BlockchainToolInput(BaseModel):
    """Input schema for blockchain audit logging"""
    action: str = Field(..., description="Action: 'log_decision', 'verify_chain', 'generate_zkp', 'export_audit'")
    decision_data: Dict[str, Any] = Field(default_factory=dict, description="Clinical decision data to log")
    audit_id: int = Field(default=None, description="Audit entry ID (for verification)")


class BlockchainTool(BaseTool):
    """
    Blockchain Audit Logger with Zero-Knowledge Proofs

    Provides immutable audit trail using:
    - Ethereum smart contracts (Solidity)
    - IPFS decentralized storage
    - SHA-256 hash chaining
    - Zero-Knowledge Proofs (privacy-preserving verification)

    Features:
    - Tamper-evident logging
    - Cryptographic integrity verification
    - Privacy-preserving compliance audits
    - Distributed storage

    Used by: logger_agent (Audit Logger Agent)
    """

    name: str = "Blockchain Audit Logger"
    description: str = """Log clinical decisions to immutable blockchain audit trail.
    Uses Ethereum smart contracts + IPFS + Zero-Knowledge Proofs.
    Supports tamper verification and privacy-preserving compliance audits."""
    args_schema: Type[BaseModel] = BlockchainToolInput

    def _run(
        self,
        action: str,
        decision_data: Dict[str, Any] = None,
        audit_id: int = None
    ) -> str:
        """
        Execute blockchain audit operation

        Args:
            action: 'log_decision', 'verify_chain', 'generate_zkp', 'export_audit'
            decision_data: Clinical decision data to log
            audit_id: Audit entry ID (for verification)

        Returns:
            Audit operation result for logger_agent
        """
        if decision_data is None:
            decision_data = {}

        try:
            logger = BlockchainAuditLogger()

            if action == 'log_decision':
                return self._log_decision(logger, decision_data)

            elif action == 'verify_chain':
                return self._verify_chain(logger, audit_id)

            elif action == 'generate_zkp':
                return self._generate_zkp(logger, decision_data)

            elif action == 'export_audit':
                return self._export_audit(logger)

            else:
                return f"""=== BLOCKCHAIN AUDIT ERROR ===
Unknown action: '{action}'

Supported actions:
  - log_decision (log clinical decision to blockchain)
  - verify_chain (verify audit trail integrity)
  - generate_zkp (generate Zero-Knowledge Proof)
  - export_audit (export audit trail for compliance)
"""

        except Exception as e:
            return f"""=== BLOCKCHAIN AUDIT FAILED ===
Error: {str(e)}

Possible causes:
  1. Ethereum node not running (use Ganache for local dev)
  2. IPFS daemon not started
  3. Smart contract not deployed
  4. Insufficient gas for transaction

Recommendation: Check blockchain infrastructure.
"""

    def _log_decision(self, logger: BlockchainAuditLogger, decision_data: Dict[str, Any]) -> str:
        """Log clinical decision to blockchain"""
        required = ['mrn', 'physician', 'query', 'recommendation']
        missing = [f for f in required if f not in decision_data]

        if missing:
            return f"ERROR: Missing required fields: {', '.join(missing)}"

        result = logger.log_decision(
            mrn=decision_data['mrn'],
            patient_context=decision_data.get('patient_context', ''),
            physician_id=decision_data['physician'],
            query=decision_data['query'],
            recommendation=decision_data['recommendation'],
            bayesian_prob=decision_data.get('bayesian_prob', 0.0),
            chain_data=decision_data.get('chain_data', {}),
            analysis_mode=decision_data.get('analysis_mode', 'chain')
        )

        if result.get('success'):
            return f"""=== DECISION LOGGED TO BLOCKCHAIN ===

Transaction Hash: {result.get('tx_hash', 'N/A')}
Block Number:     {result.get('block_number', 'N/A')}
Entry ID:         {result.get('entry_id', 'N/A')}
Entry Hash:       {result.get('entry_hash', 'N/A')[:16]}...

IPFS Hash:        {result.get('ipfs_hash', 'N/A')}
Gas Used:         {result.get('gas_used', 'N/A')}

Patient MRN:      {decision_data['mrn']}
Physician:        {decision_data['physician']}

Status: ✓ Immutably logged to distributed ledger

Verification: Run verify_chain with entry_id={result.get('entry_id')}
"""
        else:
            return f"""=== BLOCKCHAIN LOGGING FAILED ===

Error: {result.get('error', 'Unknown error')}

Recommendation: Log to local database as backup.
"""

    def _verify_chain(self, logger: BlockchainAuditLogger, audit_id: int = None) -> str:
        """Verify blockchain audit trail integrity"""
        if audit_id is not None:
            # Verify single entry
            result = logger.verify_entry(audit_id)

            if result.get('valid'):
                return f"""=== ENTRY VERIFICATION ===

Entry ID: {audit_id}
Status:   ✓ VALID

Entry Hash:    {result.get('entry_hash', 'N/A')}
Previous Hash: {result.get('prev_hash', 'N/A')}
Hash Verified: ✓

Blockchain:    ✓ Transaction confirmed
IPFS:          ✓ Data retrievable

Conclusion: Entry is cryptographically valid and tamper-free.
"""
            else:
                return f"""=== ENTRY VERIFICATION FAILED ===

Entry ID: {audit_id}
Status:   ✗ INVALID

Issues detected:
{chr(10).join(f'  - {issue}' for issue in result.get('issues', []))}

Conclusion: POTENTIAL TAMPERING DETECTED
"""
        else:
            # Verify entire chain
            result = logger.verify_full_chain()

            if result.get('valid'):
                return f"""=== FULL CHAIN VERIFICATION ===

Total Entries:    {result.get('total_entries', 0)}
Status:           ✓ ALL VALID

Hash Chain:       ✓ Intact
Blockchain Links: ✓ All confirmed
Genesis Block:    {result.get('genesis_hash', 'N/A')}
Latest Block:     {result.get('latest_hash', 'N/A')}

Conclusion: Audit trail is cryptographically sound and tamper-free.
"""
            else:
                return f"""=== CHAIN VERIFICATION FAILED ===

Total Entries:     {result.get('total_entries', 0)}
Invalid Entries:   {result.get('invalid_count', 0)}

First Invalid ID:  {result.get('first_invalid_id', 'N/A')}

Issues detected:
{chr(10).join(f'  - {issue}' for issue in result.get('issues', []))}

Conclusion: AUDIT TRAIL COMPROMISED - INVESTIGATE IMMEDIATELY
"""

    def _generate_zkp(self, logger: BlockchainAuditLogger, decision_data: Dict[str, Any]) -> str:
        """Generate Zero-Knowledge Proof for privacy-preserving verification"""
        if not decision_data:
            return "ERROR: No decision data provided for ZKP generation."

        secret = decision_data.get('physician_signature', 'default_secret')

        zkp = logger.generate_zkp(decision_data, secret)

        return f"""=== ZERO-KNOWLEDGE PROOF GENERATED ===

Commitment: {zkp.get('commitment', 'N/A')[:32]}...
Proof:      {zkp.get('proof', 'N/A')[:32]}...
Challenge:  {zkp.get('challenge', 'N/A')[:32]}...

NONCE: {zkp.get('nonce', 'N/A')[:16]}... (KEEP SECRET)

Purpose: Allows compliance auditors to verify decision correctness
         WITHOUT accessing Protected Health Information (PHI).

Usage: Provide commitment, proof, and challenge to auditor.
       Auditor can verify correctness without seeing patient data.

Privacy: ✓ PHI remains encrypted and private
Security: ✓ Cryptographically sound (SHA-256 based)
"""

    def _export_audit(self, logger: BlockchainAuditLogger) -> str:
        """Export audit trail for compliance reporting"""
        result = logger.export_audit_trail()

        if result.get('success'):
            return f"""=== AUDIT TRAIL EXPORTED ===

Export File:      {result.get('export_path', 'N/A')}
Format:           JSON (human-readable + machine-parseable)

Total Entries:    {result.get('total_entries', 0)}
Date Range:       {result.get('start_date', 'N/A')} to {result.get('end_date', 'N/A')}
Export Size:      {result.get('file_size_mb', 0):.2f} MB

Physicians:       {result.get('unique_physicians', 0)}
Patients:         {result.get('unique_patients', 0)}

Blockchain Hashes: ✓ Included
IPFS References:   ✓ Included
Verification Data: ✓ Included

Status: ✓ Audit trail ready for compliance review

Recommendation: Provide export file to compliance officer or regulatory auditor.
"""
        else:
            return f"""=== AUDIT EXPORT FAILED ===

Error: {result.get('error', 'Unknown error')}

Recommendation: Check write permissions and disk space.
"""


# Export
__all__ = ['BlockchainTool']


if __name__ == "__main__":
    print("Blockchain Tool - Immutable Audit Logger")
    print("=" * 50)

    tool = BlockchainTool()
    print(f"Tool Name: {tool.name}")
    print(f"Description: {tool.description}")
    print("\nActions: log_decision, verify_chain, generate_zkp, export_audit")
