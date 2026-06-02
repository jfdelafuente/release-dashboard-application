#!/usr/bin/env python3
"""
Backend Setup Test
Verify that all dependencies are installed and basic configuration is correct
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported"""
    print("Testing imports...")

    required_packages = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'pydantic': 'Pydantic',
        'chardet': 'Chardet',
        'dotenv': 'Python-dotenv',
    }

    failed = []
    for package, display_name in required_packages.items():
        try:
            __import__(package)
            print(f"  ✅ {display_name}")
        except ImportError as e:
            print(f"  ❌ {display_name}: {e}")
            failed.append(package)

    return len(failed) == 0

def test_directories():
    """Test that required directories exist"""
    print("\nTesting directories...")

    backend_root = Path(__file__).parent
    required_dirs = [
        'app',
        'app/routes',
        'app/services',
        'app/utils',
        'app/models',
        'app/logging',
        'tests',
    ]

    failed = []
    for dir_path in required_dirs:
        full_path = backend_root / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ (missing)")
            failed.append(dir_path)

    return len(failed) == 0

def test_files():
    """Test that required files exist"""
    print("\nTesting files...")

    backend_root = Path(__file__).parent
    required_files = [
        'app/__init__.py',
        'app/main.py',
        'requirements.txt',
        '.env.example',
        'README.md',
        'test_setup.py',
    ]

    failed = []
    for file_path in required_files:
        full_path = backend_root / file_path
        if full_path.exists() and full_path.is_file():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (missing)")
            failed.append(file_path)

    return len(failed) == 0

def test_env():
    """Test that .env file exists or .env.example is available"""
    print("\nTesting configuration...")

    backend_root = Path(__file__).parent
    env_file = backend_root / '.env'
    env_example = backend_root / '.env.example'

    if env_file.exists():
        print(f"  ✅ .env (configured)")
        return True
    elif env_example.exists():
        print(f"  ⚠️  .env.example found (need to create .env)")
        print(f"     Run: cp .env.example .env")
        return True
    else:
        print(f"  ❌ .env not found")
        return False

def main():
    """Run all setup tests"""
    print("=" * 60)
    print("CSV Upload API - Backend Setup Verification")
    print("=" * 60)

    results = {
        'imports': test_imports(),
        'directories': test_directories(),
        'files': test_files(),
        'env': test_env(),
    }

    print("\n" + "=" * 60)
    print("SETUP VERIFICATION SUMMARY")
    print("=" * 60)

    all_passed = all(results.values())

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check.upper():15} {status}")

    print("\n" + "=" * 60)

    if all_passed:
        print("✅ Backend Setup Complete!")
        print("\nNext Steps:")
        print("1. Create .env file: cp .env.example .env")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run server: python -m app.main")
        print("4. Check health: curl http://localhost:8000/health")
        return 0
    else:
        print("❌ Backend Setup Failed!")
        print("Please fix the issues above and try again.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
