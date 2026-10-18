#!/usr/bin/env python
import subprocess
import json
import os
import sys
from pathlib import Path

os.chdir("C:\\dev\\neoeve")

# Get list of test files
test_dir = Path("tests")
test_files = sorted(test_dir.glob("test_p0*.py"))

results = {
    "total_files": len(test_files),
    "files": [],
    "summary": {
        "pass": 0,
        "fail": 0,
        "error": 0,
        "skipped": 0
    },
    "failures": [],
    "errors": []
}

for test_file in test_files:
    filename = test_file.name
    print(f"Testing {filename}...", file=sys.stderr, flush=True)

    try:
        # Run pytest on this file with json output
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout + result.stderr

        # Parse output for test results
        file_results = {
            "file": filename,
            "pass": 0,
            "fail": 0,
            "error": 0,
            "skipped": 0,
            "test_names": []
        }

        # Look for test results
        for line in output.split('\n'):
            if " PASSED" in line:
                file_results["pass"] += 1
                results["summary"]["pass"] += 1
                if "::" in line:
                    test_name = line.split("::")[1].split(" ")[0]
                    file_results["test_names"].append({"name": test_name, "status": "PASS"})
            elif " FAILED" in line:
                file_results["fail"] += 1
                results["summary"]["fail"] += 1
                if "::" in line:
                    test_name = line.split("::")[1].split(" ")[0]
                    file_results["test_names"].append({"name": test_name, "status": "FAIL"})
                    results["failures"].append({
                        "file": filename,
                        "test": test_name,
                        "line": line
                    })
            elif " ERROR" in line and "ERROR at setup" not in line:
                file_results["error"] += 1
                results["summary"]["error"] += 1
                if "::" in line:
                    test_name = line.split("::")[1].split(" ")[0]
                    file_results["test_names"].append({"name": test_name, "status": "ERROR"})
                    results["errors"].append({
                        "file": filename,
                        "test": test_name,
                        "line": line
                    })
            elif "ERROR at setup" in line:
                # Setup error
                results["summary"]["error"] += 1
                if "::" in line:
                    test_name = line.split("::")[1].split(" ")[0]
                    file_results["test_names"].append({"name": test_name, "status": "ERROR"})
                    results["errors"].append({
                        "file": filename,
                        "test": test_name,
                        "type": "setup_error",
                        "line": line
                    })

        results["files"].append(file_results)

    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: {filename}", file=sys.stderr)
        results["files"].append({
            "file": filename,
            "status": "timeout"
        })
    except Exception as e:
        print(f"ERROR: {filename}: {str(e)}", file=sys.stderr)
        results["files"].append({
            "file": filename,
            "status": f"error: {str(e)}"
        })

print(json.dumps(results, indent=2))
