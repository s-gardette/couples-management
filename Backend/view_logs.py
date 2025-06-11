#!/usr/bin/env python3
"""
Simple log viewer for the Household Management App.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import argparse


def get_latest_log_file(log_pattern):
    """Get the most recent log file matching the pattern."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return None
    
    # Find all files matching the pattern
    log_files = list(logs_dir.glob(log_pattern))
    if not log_files:
        return None
    
    # Return the most recently modified file
    return max(log_files, key=lambda x: x.stat().st_mtime)


def tail_file(file_path, lines=50):
    """Display the last N lines of a file and follow new content."""
    if not file_path or not file_path.exists():
        print(f"Log file not found: {file_path}")
        return
    
    print(f"📁 Viewing: {file_path}")
    print(f"📅 Last modified: {datetime.fromtimestamp(file_path.stat().st_mtime)}")
    print("=" * 80)
    
    # Read and display the last N lines
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Get all lines
            all_lines = f.readlines()
            
            # Display the last N lines
            start_line = max(0, len(all_lines) - lines)
            for line in all_lines[start_line:]:
                print(line.rstrip())
                
        print("=" * 80)
        print("🔄 Following new log entries... (Press Ctrl+C to stop)")
        print()
        
        # Follow new content
        with open(file_path, 'r', encoding='utf-8') as f:
            # Seek to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    print(line.rstrip())
                else:
                    time.sleep(0.1)
                    
    except KeyboardInterrupt:
        print("\n👋 Log viewing stopped")
    except Exception as e:
        print(f"❌ Error reading log file: {e}")


def list_log_files():
    """List all available log files."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        print("📁 No logs directory found")
        return
    
    log_files = list(logs_dir.glob("*.log"))
    if not log_files:
        print("📁 No log files found")
        return
    
    print("📁 Available log files:")
    print()
    
    # Group by type
    log_types = {}
    for log_file in log_files:
        log_type = log_file.name.split('_')[0]
        if log_type not in log_types:
            log_types[log_type] = []
        log_types[log_type].append(log_file)
    
    for log_type, files in sorted(log_types.items()):
        print(f"  {log_type.upper()} logs:")
        for file in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
            size = file.stat().st_size
            modified = datetime.fromtimestamp(file.stat().st_mtime)
            print(f"    📄 {file.name} ({size:,} bytes, {modified.strftime('%Y-%m-%d %H:%M:%S')})")
        print()


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="View Household Management App logs")
    parser.add_argument(
        "log_type", 
        nargs="?", 
        choices=["app", "error", "access", "uvicorn", "list"], 
        default="app",
        help="Type of log to view (default: app)"
    )
    parser.add_argument(
        "-n", "--lines", 
        type=int, 
        default=50,
        help="Number of lines to display initially (default: 50)"
    )
    parser.add_argument(
        "-l", "--list", 
        action="store_true",
        help="List all available log files"
    )
    
    args = parser.parse_args()
    
    if args.list or args.log_type == "list":
        list_log_files()
        return
    
    # Get today's timestamp for log files
    timestamp = datetime.now().strftime("%Y%m%d")
    
    # Map log types to file patterns
    log_patterns = {
        "app": f"app_{timestamp}.log",
        "error": f"error_{timestamp}.log", 
        "access": f"access_{timestamp}.log",
        "uvicorn": f"uvicorn_{timestamp}.log"
    }
    
    if args.log_type not in log_patterns:
        print(f"❌ Unknown log type: {args.log_type}")
        print(f"Available types: {', '.join(log_patterns.keys())}")
        return
    
    # Find the log file
    log_file = get_latest_log_file(log_patterns[args.log_type])
    if not log_file:
        # Try to find any file of this type
        log_file = get_latest_log_file(f"{args.log_type}_*.log")
    
    if not log_file:
        print(f"❌ No {args.log_type} log files found")
        print("💡 Start the server first: python run_server.py")
        return
    
    # View the log file
    tail_file(log_file, args.lines)


if __name__ == "__main__":
    main() 