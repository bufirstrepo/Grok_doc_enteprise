"""
Peer Review Workflow Engine (v3.0)
Manages the queue of cases requiring human verification.
Features:
- Queue Management (Pending, Approved, Rejected)
- Intelligent Routing (Specialty-based)
- Audit Logging
"""

import time
import uuid
from typing import List, Dict, Optional
from datetime import datetime

class PeerReviewSystem:
    def __init__(self):
        # In-memory storage for demo (would be SQL/Redis in prod)
        self.queue = [] 
        self.history = []
        
    def submit_for_review(self, case_data: Dict, priority: str = "Normal") -> str:
        """
        Submit a case to the peer review queue.
        Returns: Review ID
        """
        review_id = str(uuid.uuid4())
        entry = {
            'id': review_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'Pending',
            'priority': priority,
            'data': case_data,
            'assigned_to': None,
            'comments': []
        }
        self.queue.append(entry)
        return review_id

    def get_queue(self, specialty: Optional[str] = None) -> List[Dict]:
        """Get pending cases, optionally filtered by specialty"""
        # Sort by priority (High > Normal)
        sorted_queue = sorted(
            self.queue, 
            key=lambda x: 0 if x['priority'] == 'High' else 1
        )
        
        if specialty:
            # Simple filter logic (assuming case_data has 'specialty' field)
            return [x for x in sorted_queue if x['data'].get('specialty') == specialty]
        return sorted_queue

    def approve_case(self, review_id: str, reviewer: str, comments: str = "") -> bool:
        """Approve a case and move to history"""
        entry = self._find_entry(review_id)
        if entry:
            entry['status'] = 'Approved'
            entry['reviewer'] = reviewer
            entry['decision_time'] = datetime.now().isoformat()
            if comments:
                entry['comments'].append(f"{reviewer}: {comments}")
            
            self.queue.remove(entry)
            self.history.append(entry)
            return True
        return False

    def reject_case(self, review_id: str, reviewer: str, reason: str) -> bool:
        """Reject a case and move to history"""
        entry = self._find_entry(review_id)
        if entry:
            entry['status'] = 'Rejected'
            entry['reviewer'] = reviewer
            entry['decision_time'] = datetime.now().isoformat()
            entry['comments'].append(f"{reviewer} REJECTED: {reason}")
            
            self.queue.remove(entry)
            self.history.append(entry)
            return True
        return False

    def _find_entry(self, review_id: str) -> Optional[Dict]:
        for entry in self.queue:
            if entry['id'] == review_id:
                return entry
        return None

    def get_stats(self) -> Dict:
        return {
            'pending': len(self.queue),
            'approved': len([x for x in self.history if x['status'] == 'Approved']),
            'rejected': len([x for x in self.history if x['status'] == 'Rejected'])
        }

if __name__ == "__main__":
    system = PeerReviewSystem()
    
    # Test submission
    rid = system.submit_for_review({
        'mrn': '12345',
        'diagnosis': 'Sepsis',
        'ai_recommendation': 'Start Vancomycin'
    }, priority="High")
    
    print(f"Submitted case {rid}")
    print(f"Queue: {len(system.get_queue())}")
    
    # Test approval
    system.approve_case(rid, "Dr. Smith", "Agreed with AI")
    print(f"Stats: {system.get_stats()}")
