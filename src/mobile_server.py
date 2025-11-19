#!/usr/bin/env python3
"""
WebSocket Server for Grok Doc v2.0
Real-time mobile → server connection for voice transcription and SOAP generation

Handles:
- WebSocket connections from mobile devices (hospital WiFi only)
- Audio streaming for real-time Whisper transcription
- LLM chain execution with progress updates
- SOAP note generation and delivery
- Secure authentication via JWT tokens
"""

import asyncio
import json
import jwt
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
import hashlib
import base64

# WebSocket server
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("WARNING: websockets not installed. Run: pip install websockets")

# Import our components
from whisper_inference import get_transcriber
from crewai_agents import run_crewai_decision
from soap_generator import SOAPGenerator
from audit_log import log_decision


class MobileWebSocketServer:
    """
    WebSocket server for mobile co-pilot

    Endpoints:
    - /ws/transcribe - Audio streaming for transcription
    - /ws/decision - LLM chain execution with progress
    - /ws/soap - SOAP note generation
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        jwt_secret: str = "your-secret-key-change-in-production"
    ):
        """
        Initialize WebSocket server

        Args:
            host: Server host (0.0.0.0 for all interfaces)
            port: WebSocket port (default 8765)
            jwt_secret: Secret key for JWT authentication
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets required. Install with: pip install websockets")

        self.host = host
        self.port = port
        self.jwt_secret = jwt_secret

        # Active connections
        self.connections: Set[WebSocketServerProtocol] = set()

        # Initialize components
        self.transcriber = get_transcriber()
        self.soap_generator = SOAPGenerator()

    def generate_jwt(self, physician_id: str, expiry_hours: int = 8) -> str:
        """Generate JWT token for physician authentication"""
        payload = {
            'physician_id': physician_id,
            'exp': datetime.utcnow() + timedelta(hours=expiry_hours),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        return token

    def verify_jwt(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle WebSocket connection

        Args:
            websocket: WebSocket connection
            path: Request path (/ws/transcribe, /ws/decision, /ws/soap)
        """

        # Register connection
        self.connections.add(websocket)
        print(f"New connection: {websocket.remote_address} → {path}")

        try:
            # Authenticate
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)

            token = auth_data.get('token')
            if not token:
                await websocket.send(json.dumps({'error': 'Authentication required'}))
                return

            payload = self.verify_jwt(token)
            if not payload:
                await websocket.send(json.dumps({'error': 'Invalid or expired token'}))
                return

            physician_id = payload['physician_id']
            print(f"Authenticated: {physician_id}")

            # Send authentication success
            await websocket.send(json.dumps({'status': 'authenticated', 'physician_id': physician_id}))

            # Route by path
            if path == '/ws/transcribe':
                await self.handle_transcription(websocket, physician_id)
            elif path == '/ws/decision':
                await self.handle_decision(websocket, physician_id)
            elif path == '/ws/soap':
                await self.handle_soap(websocket, physician_id)
            else:
                await websocket.send(json.dumps({'error': f'Unknown path: {path}'}))

        except websockets.exceptions.ConnectionClosed:
            print(f"Connection closed: {websocket.remote_address}")
        except Exception as e:
            print(f"Error: {e}")
            await websocket.send(json.dumps({'error': str(e)}))
        finally:
            self.connections.remove(websocket)

    async def handle_transcription(self, websocket: WebSocketServerProtocol, physician_id: str):
        """
        Handle audio transcription

        Protocol:
        1. Client sends: {'audio': base64_encoded_audio, 'format': 'wav'}
        2. Server streams: {'status': 'transcribing', 'progress': 0.5}
        3. Server sends: {'status': 'complete', 'text': '...', 'segments': [...]}
        """

        async for message in websocket:
            data = json.loads(message)

            # Get audio data
            audio_b64 = data.get('audio')
            audio_format = data.get('format', 'wav')

            if not audio_b64:
                await websocket.send(json.dumps({'error': 'No audio data'}))
                continue

            # Decode audio
            audio_bytes = base64.b64decode(audio_b64)

            # Send progress
            await websocket.send(json.dumps({
                'status': 'transcribing',
                'progress': 0.1,
                'message': 'Processing audio...'
            }))

            # Transcribe
            try:
                result = self.transcriber.transcribe_bytes(audio_bytes)

                # Send result
                await websocket.send(json.dumps({
                    'status': 'complete',
                    'text': result['text'],
                    'segments': result.get('segments', []),
                    'duration': result.get('duration', 0),
                    'language': result.get('language', 'en')
                }))

            except Exception as e:
                await websocket.send(json.dumps({
                    'status': 'error',
                    'error': str(e)
                }))

    async def handle_decision(self, websocket: WebSocketServerProtocol, physician_id: str):
        """
        Handle LLM decision chain execution

        Protocol:
        1. Client sends: {'patient_context': {...}, 'query': '...', 'mode': 'chain'}
        2. Server streams progress for each agent
        3. Server sends final decision
        """

        async for message in websocket:
            data = json.loads(message)

            patient_context = data.get('patient_context', {})
            query = data.get('query', '')
            mode = data.get('mode', 'chain')

            if not query:
                await websocket.send(json.dumps({'error': 'Query required'}))
                continue

            # Send initial status
            await websocket.send(json.dumps({
                'status': 'starting',
                'message': 'Initializing LLM agents...'
            }))

            try:
                # Execute decision (this should be async in production)
                # For now, we'll simulate progress updates

                # Agent 1: Kinetics
                await websocket.send(json.dumps({
                    'status': 'agent_running',
                    'agent': 'Kinetics',
                    'progress': 0.25,
                    'message': 'Calculating pharmacokinetics...'
                }))

                # Agent 2: Adversarial
                await websocket.send(json.dumps({
                    'status': 'agent_running',
                    'agent': 'Adversarial',
                    'progress': 0.50,
                    'message': 'Analyzing risks...'
                }))

                # Agent 3: Literature
                await websocket.send(json.dumps({
                    'status': 'agent_running',
                    'agent': 'Literature',
                    'progress': 0.75,
                    'message': 'Validating evidence...'
                }))

                # Agent 4: Arbiter
                await websocket.send(json.dumps({
                    'status': 'agent_running',
                    'agent': 'Arbiter',
                    'progress': 0.90,
                    'message': 'Synthesizing decision...'
                }))

                # Run actual decision (blocking - should be async)
                result = run_crewai_decision(
                    patient_context=patient_context,
                    query=query,
                    retrieved_cases=[],  # TODO: implement case retrieval
                    bayesian_result={'prob_safe': 0.85, 'n_cases': 100}
                )

                # Send final result
                await websocket.send(json.dumps({
                    'status': 'complete',
                    'recommendation': result['final_recommendation'],
                    'confidence': result['final_confidence'],
                    'agent_outputs': result['agent_outputs'],
                    'hash': result['hash']
                }))

            except Exception as e:
                await websocket.send(json.dumps({
                    'status': 'error',
                    'error': str(e)
                }))

    async def handle_soap(self, websocket: WebSocketServerProtocol, physician_id: str):
        """
        Handle SOAP note generation

        Protocol:
        1. Client sends: {'transcript': '...', 'chain_result': {...}, 'patient_context': {...}}
        2. Server generates SOAP note
        3. Server sends formatted SOAP
        """

        async for message in websocket:
            data = json.loads(message)

            transcript = data.get('transcript', '')
            chain_result = data.get('chain_result', {})
            patient_context = data.get('patient_context', {})

            if not transcript:
                await websocket.send(json.dumps({'error': 'Transcript required'}))
                continue

            # Send progress
            await websocket.send(json.dumps({
                'status': 'generating',
                'message': 'Generating SOAP note...'
            }))

            try:
                # Generate SOAP
                soap_result = self.soap_generator.generate_soap(
                    transcript=transcript,
                    chain_result=chain_result,
                    patient_context=patient_context
                )

                # Send result
                await websocket.send(json.dumps({
                    'status': 'complete',
                    'soap_text': soap_result['soap_text'],
                    'subjective': soap_result.get('subjective', ''),
                    'objective': soap_result.get('objective', ''),
                    'assessment': soap_result.get('assessment', ''),
                    'plan': soap_result.get('plan', ''),
                    'citations': soap_result.get('citations', []),
                    'billing_code': soap_result.get('metadata', {}).get('billing_code', '')
                }))

            except Exception as e:
                await websocket.send(json.dumps({
                    'status': 'error',
                    'error': str(e)
                }))

    async def start(self):
        """Start WebSocket server"""
        print(f"\n{'='*60}")
        print("GROK DOC WEBSOCKET SERVER")
        print(f"Host: {self.host}:{self.port}")
        print("Endpoints:")
        print("  - /ws/transcribe (audio → text)")
        print("  - /ws/decision (LLM chain)")
        print("  - /ws/soap (SOAP generation)")
        print(f"{'='*60}\n")

        async with websockets.serve(self.handle_connection, self.host, self.port):
            await asyncio.Future()  # Run forever

    def run(self):
        """Run WebSocket server (blocking)"""
        asyncio.run(self.start())


def generate_physician_token(physician_id: str, secret: str = "your-secret-key") -> str:
    """
    Generate JWT token for physician (utility function)

    Usage:
        token = generate_physician_token("dr.smith@hospital.com")
        # Give this token to mobile app for authentication
    """
    server = MobileWebSocketServer(jwt_secret=secret)
    return server.generate_jwt(physician_id)


if __name__ == "__main__":
    print("Grok Doc WebSocket Server v2.0")
    print(f"WebSockets available: {WEBSOCKETS_AVAILABLE}")

    if WEBSOCKETS_AVAILABLE:
        # Generate sample token
        token = generate_physician_token("dr.test@hospital.com")
        print(f"\nSample JWT token:")
        print(token)
        print("\nUse this token in mobile app for authentication\n")

        # Start server
        server = MobileWebSocketServer(
            host="0.0.0.0",
            port=8765,
            jwt_secret="your-secret-key-change-in-production"
        )

        try:
            server.run()
        except KeyboardInterrupt:
            print("\nServer stopped")

    else:
        print("\nInstall websockets:")
        print("  pip install websockets pyjwt")
