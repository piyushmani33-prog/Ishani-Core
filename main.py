#!/usr/bin/env python3
"""
Ishani-Core / TechBuzz AI — Main Entry Point

Usage:
    python main.py

This script launches the TechBuzz FastAPI backend server.
The actual application is defined in techbuzz-full/techbuzz-full/backend_python/app.py
"""

import sys
import os
import shutil
import subprocess


def main():
    """Launch the TechBuzz FastAPI backend server."""
    backend_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "techbuzz-full", "techbuzz-full", "backend_python"
    )
    app_py = os.path.join(backend_dir, "app.py")

    if not os.path.isfile(app_py):
        print("❌ Error: backend app.py not found at:")
        print(f"   {app_py}")
        print()
        print("Make sure you cloned the full repository:")
        print("  git clone https://github.com/piyushmani33-prog/Ishani-Core.git")
        sys.exit(1)

    # Check for .env
    env_file = os.path.join(backend_dir, ".env")
    env_example = os.path.join(backend_dir, ".env.example")
    if not os.path.isfile(env_file) and os.path.isfile(env_example):
        print("⚠️  No .env file found. Copying .env.example → .env")
        print("   Please edit .env and add your API keys.")
        shutil.copy2(env_example, env_file)

    # Install dependencies if requirements.txt exists
    req_file = os.path.join(backend_dir, "requirements.txt")
    if os.path.isfile(req_file):
        print("📦 Checking dependencies...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", req_file],
            cwd=backend_dir
        )

    print()
    print("🚀 Starting Ishani-Core / TechBuzz AI Server...")
    print("   http://localhost:8000")
    print()

    # Launch the app
    os.chdir(backend_dir)
    subprocess.run([sys.executable, "app.py"], cwd=backend_dir)


if __name__ == "__main__":
    main()