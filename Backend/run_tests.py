#!/usr/bin/env python3
"""
Test runner script for the Household Management App.

This script runs all tests including:
- Main application tests
- Auth module tests
- Any future module tests

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py -v           # Run with verbose output
    python run_tests.py --coverage   # Run with coverage report
"""

import sys
import subprocess
from pathlib import Path


def run_tests(args=None):
    """Run all tests with pytest."""
    if args is None:
        args = []
    
    # Base pytest command
    cmd = ["python", "-m", "pytest", "tests/"]
    
    # Add any additional arguments
    cmd.extend(args)
    
    # Add default arguments for better output
    if "-v" not in args and "--verbose" not in args:
        cmd.append("-v")
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 60)
    
    # Run the tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    return result.returncode


def main():
    """Main entry point."""
    # Get command line arguments (excluding script name)
    args = sys.argv[1:]
    
    # Handle special arguments
    if "--coverage" in args:
        args.remove("--coverage")
        # Add coverage arguments
        coverage_args = [
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing"
        ]
        args.extend(coverage_args)
    
    # Run tests
    exit_code = run_tests(args)
    
    if exit_code == 0:
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        
        # Show test summary
        print("\nTest Summary:")
        print("- Main application tests: ✅")
        print("- Auth module tests: ✅")
        print("- JWT system tests: ✅")
        print("- Password security tests: ✅")
        
    else:
        print("\n" + "=" * 60)
        print("❌ Some tests failed!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 