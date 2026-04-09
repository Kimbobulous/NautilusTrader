from __future__ import annotations

from mgc_bt.validation.preflight import PreflightReport


def render_health_report(*reports: PreflightReport) -> str:
    lines = ["System health summary"]
    for report in reports:
        status = "READY" if report.ok else "MISSING"
        if report.ok and report.warnings:
            status = "ATTENTION"
        lines.append(f"{report.command}: {status}")
        for issue in report.failures:
            lines.append(f"  missing: {issue.message}")
            if issue.fix:
                lines.append(f"  fix: {issue.fix}")
        for issue in report.warnings:
            lines.append(f"  attention: {issue.message}")
            if issue.fix:
                lines.append(f"  note: {issue.fix}")
    return "\n".join(lines)
