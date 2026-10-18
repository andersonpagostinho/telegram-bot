#!/usr/bin/env python
import subprocess
import json
import os
import sys
import re
from pathlib import Path

os.chdir("C:\\dev\\neoeve")

# Get list of test files
test_dir = Path("tests")
test_files = sorted([f for f in test_dir.glob("test_p0*.py") if f.is_file()])

results = {
    "total_files": len(test_files),
    "summary": {
        "pass": 0,
        "fail": 0,
        "error": 0,
    },
    "failures": [],
    "errors": [],
    "files_with_issues": []
}

for test_file in test_files:
    filename = test_file.name
    print(f"Testing {filename}...", file=sys.stderr, flush=True)

    try:
        # Run pytest on this file
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout + result.stderr

        # Look for FAILED and ERROR patterns
        for line in output.split('\n'):
            # FAILED pattern
            if " FAILED " in line and "::" in line:
                parts = line.split("::")
                if len(parts) >= 2:
                    test_class = parts[0].split("/")[-1].replace(".py", "")
                    test_name = "::".join(parts[1:]).split(" ")[0]
                    results["summary"]["fail"] += 1
                    results["failures"].append({
                        "file": filename,
                        "test_class": test_class,
                        "test_name": test_name,
                        "full_line": line.strip()
                    })

            # ERROR at setup pattern
            if "ERROR at setup" in line and "::" in line:
                parts = line.split("::")
                if len(parts) >= 2:
                    test_class = parts[0].split()[-1]
                    test_name = "::".join(parts[1:]).split(" ")[0]
                    results["summary"]["error"] += 1
                    results["errors"].append({
                        "file": filename,
                        "test_class": test_class,
                        "test_name": test_name,
                        "type": "setup_error",
                        "full_line": line.strip()
                    })

            # ERROR pattern (not setup)
            elif " ERROR " in line and "::" in line and "ERROR at setup" not in line:
                parts = line.split("::")
                if len(parts) >= 2:
                    test_class = parts[0].split("/")[-1].replace(".py", "")
                    test_name = "::".join(parts[1:]).split(" ")[0]
                    results["summary"]["error"] += 1
                    results["errors"].append({
                        "file": filename,
                        "test_class": test_class,
                        "test_name": test_name,
                        "type": "runtime_error",
                        "full_line": line.strip()
                    })

            # Count PASS
            if " PASSED" in line:
                results["summary"]["pass"] += 1

        # If file has failures or errors, add to list
        if results["failures"][-10:] or results["errors"][-10:]:
            file_fails = [f for f in results["failures"] if f["file"] == filename]
            file_errors = [e for e in results["errors"] if e["file"] == filename]
            if file_fails or file_errors:
                results["files_with_issues"].append({
                    "file": filename,
                    "fails": len(file_fails),
                    "errors": len(file_errors)
                })

    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: {filename}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: {filename}: {str(e)}", file=sys.stderr)

print(json.dumps(results, indent=2, ensure_ascii=False))
