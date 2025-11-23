#!/usr/bin/env python3
"""
Grok Doc v2.0 Enterprise - Main Entry Point
Unified launch for all services and components
"""

import argparse
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def launch_streamlit_ui(port: int = 8501):
    """Launch Streamlit web interface"""
    print(f"🚀 Launching Streamlit UI on port {port}...")
    os.system(f"streamlit run app.py --server.port {port}")

def launch_mobile_server(port: int = 8765):
    """Launch WebSocket mobile server"""
    print(f"📱 Launching Mobile WebSocket Server on port {port}...")
    import asyncio
    from src.mobile_server import MobileWebSocketServer

    server = MobileWebSocketServer(port=port)
    asyncio.run(server.start())

def launch_mobile_ui(port: int = 8502):
    """Launch mobile co-pilot interface"""
    print(f"📱 Launching Mobile Co-Pilot UI on port {port}...")
    os.system(f"streamlit run mobile_note.py --server.port {port}")

def run_tests(test_type: str = "all"):
    """Run test suites"""
    print(f"🧪 Running {test_type} tests...")

    if test_type in ("all", "structure"):
        print("\n" + "=" * 70)
        print("CODE STRUCTURE VERIFICATION")
        print("=" * 70)
        os.system("python3 test_code_structure.py")

    if test_type in ("all", "integration"):
        print("\n" + "=" * 70)
        print("INTEGRATION TESTS")
        print("=" * 70)
        os.system("python3 test_integration_v2.py")

    if test_type in ("all", "v2"):
        print("\n" + "=" * 70)
        print("V2 FEATURE TESTS")
        print("=" * 70)
        os.system("python3 test_v2.py")

def verify_system():
    """Verify system readiness"""
    print("🔍 Verifying system components...")
    print("\n" + "=" * 70)
    print("SYSTEM VERIFICATION")
    print("=" * 70)

    # Check Python version
    import sys
    print(f"\n✓ Python: {sys.version.split()[0]}")

    # Check critical dependencies
    deps = {
        'streamlit': 'Streamlit UI framework',
        'crewai': 'CrewAI multi-agent orchestration',
        'faiss': 'FAISS vector database',
        'torch': 'PyTorch (for MONAI/XGBoost)',
        'pymc': 'PyMC (Bayesian analysis)',
        'websockets': 'WebSocket server',
        'web3': 'Web3 (blockchain)',
    }

    installed = []
    missing = []

    for dep, description in deps.items():
        try:
            __import__(dep)
            print(f"✓ {dep}: {description}")
            installed.append(dep)
        except ImportError:
            print(f"✗ {dep}: NOT INSTALLED - {description}")
            missing.append(dep)
        except Exception as e:
            if 'cffi' in str(e) or 'cryptography' in str(e):
                print(f"⚠ {dep}: Installed but backend issue")
                missing.append(dep)
            else:
                print(f"✗ {dep}: Error - {str(e)[:50]}")
                missing.append(dep)

    # Check services
    print("\n" + "=" * 70)
    print("EXTERNAL SERVICES")
    print("=" * 70)

    services = {
        'vLLM': 'local_inference.py',
        'Neo4j': 'src/services/neo4j_validator.py',
        'Ethereum': 'blockchain_audit.py',
        'IPFS': 'blockchain_audit.py (IPFS client)'
    }

    for service, file in services.items():
        print(f"⚠ {service}: Check manually ({file})")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Installed: {len(installed)}/{len(deps)} dependencies")
    print(f"Missing:   {len(missing)}/{len(deps)} dependencies")

    if missing:
        print("\n⚠ Install missing dependencies:")
        print("  pip install -r requirements.txt")

    print("\n✓ System verification complete")
    return len(missing) == 0

def show_status():
    """Show current system status"""
    print("=" * 70)
    print("GROK DOC v2.0 ENTERPRISE - SYSTEM STATUS")
    print("=" * 70)

    # Check if processes are running
    print("\nRunning Services:")
    os.system("ps aux | grep -E '(streamlit|python.*mobile)' | grep -v grep || echo '  No services running'")

    # Show git status
    print("\nGit Status:")
    os.system("git status --short || echo '  Not a git repository'")

    # Show recent commits
    print("\nRecent Commits:")
    os.system("git log --oneline -5 2>/dev/null || echo '  No git history'")

    print("\n" + "=" * 70)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Grok Doc v2.0 Enterprise - Unified Medical AI System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py ui              # Launch Streamlit UI
  python src/main.py mobile-server   # Launch WebSocket server for mobile
  python src/main.py mobile-ui       # Launch mobile co-pilot interface
  python src/main.py test            # Run all tests
  python src/main.py verify          # Verify system readiness
  python src/main.py status          # Show system status

Full deployment (requires docker-compose):
  docker-compose up                  # Launch all services
        """
    )

    parser.add_argument(
        'command',
        choices=['ui', 'mobile-server', 'mobile-ui', 'test', 'verify', 'status', 'all'],
        help='Command to execute'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Port number (default: 8501 for UI, 8502 for mobile-ui, 8765 for mobile-server)'
    )

    parser.add_argument(
        '--test-type',
        choices=['all', 'structure', 'integration', 'v2'],
        default='all',
        help='Type of tests to run (default: all)'
    )

    args = parser.parse_args()

    # Set default ports
    if args.command == 'ui':
        port = args.port or 8501
        launch_streamlit_ui(port)

    elif args.command == 'mobile-server':
        port = args.port or 8765
        launch_mobile_server(port)

    elif args.command == 'mobile-ui':
        port = args.port or 8502
        launch_mobile_ui(port)

    elif args.command == 'test':
        run_tests(args.test_type)

    elif args.command == 'verify':
        success = verify_system()
        sys.exit(0 if success else 1)

    elif args.command == 'status':
        show_status()

    elif args.command == 'all':
        print("🚀 Launching ALL services (use Ctrl+C to stop)...")
        print("\nStarting in separate processes:")
        print("  - Streamlit UI (port 8501)")
        print("  - Mobile Co-Pilot UI (port 8502)")
        print("  - WebSocket Server (port 8765)")
        print("\nRecommended: Use docker-compose for production deployment")
        print("  docker-compose up")
        sys.exit(0)

if __name__ == '__main__':
    main()
