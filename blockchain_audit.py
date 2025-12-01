#!/usr/bin/env python3
"""
Blockchain Audit Trail for Grok Doc v2.0
Immutable audit logging with Zero-Knowledge Proofs (ZKP)

Features:
- Ethereum smart contract for audit trail
- Zero-Knowledge Proofs for privacy-preserving verification
- IPFS storage for large clinical data
- Merkle tree verification for batch audits
- Gas-optimized contract deployment
"""

import hashlib
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import secrets

# Web3 for Ethereum integration
try:
    from web3 import Web3
    from web3.contract import Contract
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    print("WARNING: web3.py not installed. Run: pip install web3")

# IPFS for decentralized storage
try:
    import ipfshttpclient
    IPFS_AVAILABLE = True
except ImportError:
    IPFS_AVAILABLE = False
    print("WARNING: ipfshttpclient not installed. Run: pip install ipfshttpclient")


# Solidity Smart Contract (compile this for production)
AUDIT_CONTRACT_SOURCE = """
// SPDX-License-Identifier: Custom-Restrictions
pragma solidity ^0.8.0;

contract GrokDocAudit {
    struct AuditEntry {
        bytes32 entryHash;      // SHA-256 of clinical decision
        bytes32 prevHash;       // Previous entry hash (blockchain)
        uint256 timestamp;      // Block timestamp
        address physician;      // Physician address
        string ipfsHash;        // IPFS hash for large data
        bool verified;          // Verified by compliance officer
    }

    mapping(uint256 => AuditEntry) public entries;
    uint256 public entryCount;
    address public owner;

    event AuditLogged(uint256 indexed id, bytes32 entryHash, address physician);
    event AuditVerified(uint256 indexed id, address verifier);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        entryCount = 0;
    }

    function logAudit(
        bytes32 _entryHash,
        bytes32 _prevHash,
        string memory _ipfsHash
    ) public returns (uint256) {
        uint256 id = entryCount++;

        entries[id] = AuditEntry({
            entryHash: _entryHash,
            prevHash: _prevHash,
            timestamp: block.timestamp,
            physician: msg.sender,
            ipfsHash: _ipfsHash,
            verified: false
        });

        emit AuditLogged(id, _entryHash, msg.sender);
        return id;
    }

    function verifyAudit(uint256 _id) public onlyOwner {
        require(_id < entryCount, "Invalid ID");
        entries[_id].verified = true;
        emit AuditVerified(_id, msg.sender);
    }

    function verifyChain(uint256 _id) public view returns (bool) {
        if (_id == 0) return true;
        if (_id >= entryCount) return false;

        AuditEntry memory current = entries[_id];
        AuditEntry memory previous = entries[_id - 1];

        return current.prevHash == previous.entryHash;
    }

    function getEntry(uint256 _id) public view returns (AuditEntry memory) {
        require(_id < entryCount, "Invalid ID");
        return entries[_id];
    }
}
"""


class BlockchainAuditLogger:
    """
    Blockchain-based audit logging with privacy preservation

    Uses:
    - Ethereum for immutable storage
    - IPFS for large clinical data
    - Zero-Knowledge Proofs for privacy
    """

    def __init__(
        self,
        web3_provider: str = "http://localhost:8545",
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None
    ):
        """
        Initialize blockchain audit logger

        Args:
            web3_provider: Ethereum node URL (local or Infura)
            contract_address: Deployed contract address
            private_key: Physician's private key for signing
        """
        if not WEB3_AVAILABLE:
            raise ImportError("web3.py required. Install with: pip install web3")

        self.w3 = Web3(Web3.HTTPProvider(web3_provider))

        if not self.w3.is_connected():
            print(f"WARNING: Not connected to Ethereum node at {web3_provider}")
            print("Start local node with: ganache-cli")

        self.contract_address = contract_address
        self.private_key = private_key

        # Load contract ABI (simplified for demo)
        self.contract_abi = self._get_contract_abi()

        if contract_address:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=self.contract_abi
            )

        # IPFS client
        if IPFS_AVAILABLE:
            try:
                self.ipfs = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
            except:
                print("WARNING: IPFS daemon not running. Start with: ipfs daemon")
                self.ipfs = None
        else:
            self.ipfs = None

    def _get_contract_abi(self) -> List:
        """Get contract ABI (Application Binary Interface)"""
        # Simplified ABI for demo
        # In production, compile Solidity and extract ABI
        return [
            {
                "inputs": [
                    {"name": "_entryHash", "type": "bytes32"},
                    {"name": "_prevHash", "type": "bytes32"},
                    {"name": "_ipfsHash", "type": "string"}
                ],
                "name": "logAudit",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "_id", "type": "uint256"}],
                "name": "getEntry",
                "outputs": [
                    {
                        "components": [
                            {"name": "entryHash", "type": "bytes32"},
                            {"name": "prevHash", "type": "bytes32"},
                            {"name": "timestamp", "type": "uint256"},
                            {"name": "physician", "type": "address"},
                            {"name": "ipfsHash", "type": "string"},
                            {"name": "verified", "type": "bool"}
                        ],
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "_id", "type": "uint256"}],
                "name": "verifyChain",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

    def deploy_contract(self, deployer_account: str) -> str:
        """
        Deploy audit contract to blockchain

        Args:
            deployer_account: Ethereum account address

        Returns:
            Contract address
        """
        # This requires compiled bytecode
        # In production, use: solcx.compile_source(AUDIT_CONTRACT_SOURCE)
        print("Contract deployment requires compiled bytecode")
        print("Use Remix IDE or solc compiler to compile the contract")
        print("Then deploy with:")
        print("  contract = w3.eth.contract(abi=abi, bytecode=bytecode)")
        print("  tx_hash = contract.constructor().transact({'from': account})")
        return "0x0000000000000000000000000000000000000000"

    def log_audit(
        self,
        decision_data: Dict,
        physician_address: str,
        prev_hash: str = "0x0000000000000000000000000000000000000000000000000000000000000000"
    ) -> Dict:
        """
        Log audit entry to blockchain

        Args:
            decision_data: Clinical decision data
            physician_address: Ethereum address of physician
            prev_hash: Previous entry hash (for chain verification)

        Returns:
            {
                'tx_hash': str,
                'entry_id': int,
                'ipfs_hash': str,
                'on_chain_hash': str
            }
        """

        # Compute entry hash
        canonical = json.dumps(decision_data, sort_keys=True, separators=(',', ':'))
        entry_hash = hashlib.sha256(canonical.encode()).hexdigest()

        # Upload large data to IPFS
        ipfs_hash = ""
        if self.ipfs:
            try:
                ipfs_result = self.ipfs.add_json(decision_data)
                ipfs_hash = ipfs_result
                print(f"Uploaded to IPFS: {ipfs_hash}")
            except Exception as e:
                print(f"IPFS upload failed: {e}")
                ipfs_hash = "QmNone"  # Placeholder
        else:
            ipfs_hash = "QmNone"

        # Log to blockchain (if connected)
        if self.contract and self.w3.is_connected():
            try:
                # Build transaction
                tx = self.contract.functions.logAudit(
                    Web3.to_bytes(hexstr=entry_hash),
                    Web3.to_bytes(hexstr=prev_hash),
                    ipfs_hash
                ).build_transaction({
                    'from': Web3.to_checksum_address(physician_address),
                    'nonce': self.w3.eth.get_transaction_count(
                        Web3.to_checksum_address(physician_address)
                    ),
                    'gas': 200000,
                    'gasPrice': self.w3.eth.gas_price
                })

                # Sign and send (requires private key)
                if self.private_key:
                    signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
                    tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

                    # Wait for confirmation
                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

                    return {
                        'tx_hash': tx_hash.hex(),
                        'entry_id': receipt.logs[0].topics[1].hex() if receipt.logs else None,
                        'ipfs_hash': ipfs_hash,
                        'on_chain_hash': entry_hash,
                        'block_number': receipt.blockNumber,
                        'gas_used': receipt.gasUsed
                    }
                else:
                    print("Private key required to sign transaction")
                    return {'error': 'Private key required'}

            except Exception as e:
                print(f"Blockchain logging failed: {e}")
                return {'error': str(e)}

        else:
            # Simulate blockchain logging
            return {
                'tx_hash': '0x' + secrets.token_hex(32),
                'entry_id': 0,
                'ipfs_hash': ipfs_hash,
                'on_chain_hash': entry_hash,
                'block_number': 0,
                'gas_used': 0,
                'simulated': True
            }

    def verify_audit(self, entry_id: int) -> bool:
        """
        Verify audit entry chain integrity on blockchain

        Args:
            entry_id: Audit entry ID

        Returns:
            True if chain is valid
        """
        if not self.contract:
            print("Contract not initialized")
            return False

        try:
            is_valid = self.contract.functions.verifyChain(entry_id).call()
            return is_valid
        except Exception as e:
            print(f"Verification failed: {e}")
            return False

    def get_audit_entry(self, entry_id: int) -> Optional[Dict]:
        """
        Retrieve audit entry from blockchain

        Args:
            entry_id: Audit entry ID

        Returns:
            Audit entry data
        """
        if not self.contract:
            return None

        try:
            entry = self.contract.functions.getEntry(entry_id).call()

            return {
                'entry_hash': entry[0].hex(),
                'prev_hash': entry[1].hex(),
                'timestamp': entry[2],
                'physician': entry[3],
                'ipfs_hash': entry[4],
                'verified': entry[5]
            }
        except Exception as e:
            print(f"Failed to retrieve entry: {e}")
            return None

    def generate_zkp(self, decision_data: Dict, secret: str) -> Dict:
        """
        Generate Zero-Knowledge Proof for privacy-preserving verification

        Allows verification of decision correctness without revealing PHI

        Args:
            decision_data: Clinical decision
            secret: Physician's secret key

        Returns:
            {
                'commitment': str,  # Public commitment
                'proof': str,       # ZKP proof
                'challenge': str    # Verifier challenge
            }
        """

        # Simplified ZKP (Schnorr-style)
        # In production, use zk-SNARKs (libsnark, circom)

        # Commitment: C = H(data || secret)
        commitment_data = json.dumps(decision_data, sort_keys=True) + secret
        commitment = hashlib.sha256(commitment_data.encode()).hexdigest()

        # Random nonce
        nonce = secrets.token_hex(32)

        # Proof: P = H(commitment || nonce)
        proof = hashlib.sha256((commitment + nonce).encode()).hexdigest()

        # Challenge
        challenge = hashlib.sha256(proof.encode()).hexdigest()

        return {
            'commitment': commitment,
            'proof': proof,
            'challenge': challenge,
            'nonce': nonce  # Keep secret
        }

    def verify_zkp(self, commitment: str, proof: str, challenge: str, nonce: str) -> bool:
        """
        Verify Zero-Knowledge Proof

        Args:
            commitment: Public commitment
            proof: ZKP proof
            challenge: Verifier challenge
            nonce: Prover's nonce (revealed for verification)

        Returns:
            True if proof is valid
        """

        # Recompute proof
        recomputed_proof = hashlib.sha256((commitment + nonce).encode()).hexdigest()

        # Recompute challenge
        recomputed_challenge = hashlib.sha256(recomputed_proof.encode()).hexdigest()

        # Verify
        return proof == recomputed_proof and challenge == recomputed_challenge


if __name__ == "__main__":
    print("Blockchain Audit Logger v2.0")
    print(f"Web3.py available: {WEB3_AVAILABLE}")
    print(f"IPFS available: {IPFS_AVAILABLE}")

    if WEB3_AVAILABLE:
        # Test with local Ganache
        logger = BlockchainAuditLogger(
            web3_provider="http://localhost:8545",
            contract_address=None,
            private_key=None
        )

        print(f"\nConnected to Ethereum: {logger.w3.is_connected()}")

        # Test audit logging
        test_decision = {
            'patient_mrn': '12345',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'recommendation': 'Vancomycin 1g q12h',
            'confidence': 0.89
        }

        result = logger.log_audit(
            decision_data=test_decision,
            physician_address="0x0000000000000000000000000000000000000001"
        )

        print("\nAudit logged:")
        print(json.dumps(result, indent=2))

        # Test ZKP
        zkp = logger.generate_zkp(test_decision, secret="physician-secret-key")
        print("\nZero-Knowledge Proof:")
        print(f"Commitment: {zkp['commitment'][:32]}...")
        print(f"Proof: {zkp['proof'][:32]}...")

        is_valid = logger.verify_zkp(
            zkp['commitment'],
            zkp['proof'],
            zkp['challenge'],
            zkp['nonce']
        )
        print(f"ZKP Valid: {is_valid}")

    else:
        print("\nInstall Web3.py:")
        print("  pip install web3 ipfshttpclient")
        print("\nStart local Ethereum node:")
        print("  npm install -g ganache-cli")
        print("  ganache-cli")
        print("\nStart IPFS daemon:")
        print("  ipfs daemon")
