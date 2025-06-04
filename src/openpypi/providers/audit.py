import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def check_tool_availability() -> Dict[str, bool]:
    """Check which security tools are available on the system."""
    tools = {
        "trivy": shutil.which("trivy") is not None,
        "docker": shutil.which("docker") is not None,
        "docker-bench-security": shutil.which("docker-bench-security") is not None,
    }
    return tools


def run_trivy_scan(target: str, scan_type: str = "image") -> Optional[Dict[str, Any]]:
    """Run Trivy security scan with error handling."""
    try:
        cmd = ["trivy", scan_type, "--format", "json", "--severity", "HIGH,CRITICAL", target]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Trivy scan failed: {result.stderr}")
            return None

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Trivy scan error: {e}")
        return None


def run_docker_security_check() -> Optional[str]:
    """Run basic Docker security checks (fallback for docker-bench-security)."""
    try:
        # Check Docker daemon configuration
        result = subprocess.run(
            ["docker", "system", "info", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            docker_info = json.loads(result.stdout)

            # Basic security checks
            security_report = []

            # Check if Docker is running as root
            if docker_info.get("SecurityOptions"):
                security_report.append("Docker security options enabled")
            else:
                security_report.append("Warning: No Docker security options detected")

            # Check for user namespaces
            if "userns" in str(docker_info.get("SecurityOptions", [])):
                security_report.append("User namespaces enabled")
            else:
                security_report.append("Warning: User namespaces not enabled")

            return "\n".join(security_report)
        else:
            return "Docker security check failed"

    except Exception as e:
        return f"Docker security check error: {e}"


def generate_security_report(target_image: str = "openpypi:latest") -> Path:
    """Generate comprehensive security audit report with graceful degradation."""

    # Check tool availability
    available_tools = check_tool_availability()
    print(f"Available security tools: {available_tools}")

    # Initialize SARIF report
    sarif_report = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [],
    }

    # Run Trivy image scan if available
    if available_tools["trivy"] and available_tools["docker"]:
        print("Running Trivy image scan...")
        trivy_results = run_trivy_scan(target_image, "image")
        if trivy_results:
            sarif_report["runs"].append(
                {
                    "tool": {
                        "driver": {
                            "name": "trivy-image",
                            "version": subprocess.run(
                                ["trivy", "--version"], capture_output=True, text=True
                            ).stdout.split("\n")[0],
                        }
                    },
                    "results": trivy_results.get("Results", []),
                }
            )

        # Run Trivy filesystem scan
        print("Running Trivy filesystem scan...")
        trivy_fs_results = run_trivy_scan(".", "fs")
        if trivy_fs_results:
            sarif_report["runs"].append(
                {
                    "tool": {
                        "driver": {
                            "name": "trivy-fs",
                            "version": subprocess.run(
                                ["trivy", "--version"], capture_output=True, text=True
                            ).stdout.split("\n")[0],
                        }
                    },
                    "results": trivy_fs_results.get("Results", []),
                }
            )

    # Run Docker security check
    if available_tools["docker"]:
        print("Running Docker security checks...")
        docker_security = run_docker_security_check()
        if docker_security:
            sarif_report["runs"].append(
                {
                    "tool": {"driver": {"name": "docker-security", "version": "1.0.0"}},
                    "results": [{"message": {"text": docker_security}, "level": "info"}],
                }
            )

    # Write report
    report_path = Path("security-report.sarif")
    report_path.write_text(json.dumps(sarif_report, indent=2))

    print(f"Security report generated: {report_path}")
    return report_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate security audit report")
    parser.add_argument("--target", default="openpypi:latest", help="Target image to scan")
    parser.add_argument("--output", default="security-report.sarif", help="Output file path")
    parser.add_argument("--report-format", default="sarif", help="Report format")

    args = parser.parse_args()

    report_path = generate_security_report(args.target)
    if args.output != "security-report.sarif":
        import shutil

        shutil.move(report_path, args.output)

    print(f"Security audit complete. Report saved to: {args.output}")
