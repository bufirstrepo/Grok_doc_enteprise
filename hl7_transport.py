"""
HL7 v2.x Transport Layer (v3.0)
Implements Minimal Lower Layer Protocol (MLLP) for HL7 messaging.
Supports ADT (Admission), ORU (Results), and ORM (Orders).
"""

import socket
import threading
from typing import Dict, Optional

# MLLP Constants
SB = b'\x0b'  # Start Block
EB = b'\x1c'  # End Block
CR = b'\x0d'  # Carriage Return

class HL7MessageBuilder:
    """Helper to build simple HL7 v2 messages"""
    
    @staticmethod
    def create_ack(original_msg: str) -> str:
        """Create AA (Application Accept) ACK for a received message"""
        segments = original_msg.split('\r')
        msh = segments[0].split('|')
        
        # MSH|^~\&|GrokDoc|Hospital|EHR|Hospital|202511281200||ACK|MSG001|P|2.5
        ack_msh = f"MSH|^~\\&|GrokDoc|Hospital|{msh[2]}|{msh[3]}|{msh[6]}||ACK|{msh[9]}|P|2.5"
        # MSA|AA|MSG001
        ack_msa = f"MSA|AA|{msh[9]}"
        
        return f"{ack_msh}\r{ack_msa}\r"

    @staticmethod
    def parse_message(msg: str) -> Dict:
        """Parse HL7 message into dictionary"""
        parsed = {'segments': []}
        segments = msg.split('\r')
        
        for seg in segments:
            if not seg: continue
            fields = seg.split('|')
            seg_type = fields[0]
            parsed['segments'].append({'type': seg_type, 'fields': fields})
            
            if seg_type == 'MSH':
                parsed['type'] = fields[8] # Message Type (ADT, ORU, etc)
                parsed['control_id'] = fields[9]
            elif seg_type == 'PID':
                parsed['mrn'] = fields[3]
                # PID-5 is Patient Name (Family^Given^...)
                parsed['name'] = fields[5]
            elif seg_type == 'OBX':
                # Observation/Result
                if 'results' not in parsed: parsed['results'] = []
                parsed['results'].append({
                    'test': fields[3],
                    'value': fields[5],
                    'units': fields[6] if len(fields) > 6 else ''
                })
                
        return parsed

class MLLPServer:
    """
    Async MLLP Server to receive HL7 messages.
    Runs in a background thread.
    """
    
    def __init__(self, host='0.0.0.0', port=2575):
        self.host = host
        self.port = port
        self.running = False
        self.messages = [] # Queue of received messages
        self.sock = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

    def _run_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
            # print(f"MLLP Server listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    conn, addr = self.sock.accept()
                    self._handle_client(conn)
                except OSError:
                    break # Socket closed
        except Exception as e:
            print(f"MLLP Server Error: {e}")

    def _handle_client(self, conn):
        buffer = b""
        with conn:
            while True:
                chunk = conn.recv(4096)
                if not chunk: break
                buffer += chunk
                
                # Check for MLLP envelope
                if SB in buffer and EB in buffer:
                    start = buffer.find(SB)
                    end = buffer.find(EB)
                    
                    if start != -1 and end != -1:
                        # Extract message
                        raw_msg = buffer[start+1:end].decode('utf-8')
                        # Parse and store
                        parsed = HL7MessageBuilder.parse_message(raw_msg)
                        self.messages.append(parsed)
                        
                        # Send ACK
                        ack = HL7MessageBuilder.create_ack(raw_msg)
                        response = SB + ack.encode('utf-8') + EB + CR
                        conn.sendall(response)
                        
                        # Clear buffer (handle multiple msgs?)
                        buffer = buffer[end+2:]

if __name__ == "__main__":
    # Test Server
    server = MLLPServer(port=2576) # Use non-standard port for test
    server.start()
    
    # Test Client
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('localhost', 2576))
    
    msg = "MSH|^~\\&|Sender|Fac|Grok|Fac|20251128||ADT^A01|MSG001|P|2.5\rPID|||12345||Doe^John||19800101|M\r"
    mllp_msg = SB + msg.encode('utf-8') + EB + CR
    client.sendall(mllp_msg)
    
    resp = client.recv(1024)
    print(f"Received ACK: {resp}")
    
    import time
    time.sleep(1)
    print(f"Server Messages: {server.messages}")
    
    server.stop()
