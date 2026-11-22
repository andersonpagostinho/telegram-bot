"""
Evidence Collector - Aggregate evidence from Markdown files
"""

import os
import re
from pathlib import Path

class EvidenceCollector:
    """Collect and validate evidence from task documentation"""

    @staticmethod
    def collect_evidence(evidence_files: list, tenant_id: str = None) -> dict:
        """Collect evidence from Markdown files"""

        evidence = {
            "files_found": 0,
            "files_readable": 0,
            "content": [],
            "tests_found": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "critical_issues": [],
            "architecture_violations": []
        }

        for file_path in evidence_files:
            try:
                if os.path.exists(file_path):
                    evidence["files_found"] += 1
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        evidence["files_readable"] += 1
                        evidence["content"].append({
                            "file": file_path,
                            "length": len(content)
                        })

                        # Extract test counts
                        tests_pass = len(re.findall(r'PASS|✅', content))
                        tests_fail = len(re.findall(r'FAIL|❌', content))
                        evidence["tests_found"] += len(re.findall(r'TEST \d+', content))
                        evidence["tests_passed"] += tests_pass
                        evidence["tests_failed"] += tests_fail

                        # Check for issues
                        if "CRITICAL" in content:
                            evidence["critical_issues"].append(f"Found in {file_path}")
                        if "violat" in content.lower():
                            evidence["architecture_violations"].append(f"Found in {file_path}")

                        # Validate tenant isolation if tenant_id provided
                        if tenant_id and f"tenant_id" in content:
                            if tenant_id not in content:
                                evidence["architecture_violations"].append(f"Tenant ID mismatch in {file_path}")

            except Exception as e:
                evidence["architecture_violations"].append(f"Error reading {file_path}: {str(e)}")

        return evidence

    @staticmethod
    def validate_evidence_completeness(evidence: dict, required_files: int = 3) -> bool:
        """Check if evidence is complete"""
        return evidence["files_found"] >= required_files and evidence["files_readable"] > 0
