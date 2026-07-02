import os
import sys
import subprocess
import json
import re
from datetime import datetime

def run_quality_audit(workspace_path: str, target_path: str):
    os.chdir(workspace_path)
    
    python_exe = os.path.join(workspace_path, ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = "python"
        
    comments_script = os.path.join(workspace_path, ".agents", "plugins", "testing-plugin", "skills", "comments-check", "scripts", "check_comments.py")
    security_script = os.path.join(workspace_path, ".agents", "plugins", "testing-plugin", "skills", "security-audit", "scripts", "run_audit.py")
    
    # 1. Execute Comments Check
    # We audit "backend" for comment density as agreed in the plan
    comments_target = "backend"
    print(f"Running comments check on: {comments_target}")
    cmd_comments = [python_exe, comments_script, comments_target]
    res_comments = subprocess.run(cmd_comments, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    comment_ratio = 0.0
    comment_passed = False
    
    for line in res_comments.stdout.splitlines():
        if line.startswith("COMMENT_RATIO:"):
            try:
                comment_ratio = float(line.split(":")[1].replace("%", "").strip())
            except ValueError:
                pass
        elif line.startswith("DENSITY_CHECK:"):
            comment_passed = line.split(":")[1].strip() == "PASSED"

    # 2. Execute Security Audit
    # We audit target_path (which is the whole project root, or backend/frontend)
    print(f"Running security audit on: {target_path}")
    cmd_security = [python_exe, security_script, target_path]
    res_security = subprocess.run(cmd_security, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    security_passed = True
    actual_security_findings = []
    
    # Parse findings
    in_findings = False
    for line in res_security.stdout.splitlines():
        if line.strip() == "FINDINGS_START":
            in_findings = True
            continue
        if line.strip() == "FINDINGS_END":
            in_findings = False
            continue
        if in_findings and line.startswith("FILE:"):
            # Parse finding info: FILE:path|LINE:num|TYPE:t|SEVERITY:s|DESC:d|CODE:c
            parts = line.split("|")
            finding_data = {}
            for part in parts:
                if ":" in part:
                    k, v = part.split(":", 1)
                    finding_data[k.strip().upper()] = v.strip()
            
            filepath = finding_data.get("FILE", "")
            severity = finding_data.get("SEVERITY", "")
            
            # Apply security filter: Ignore findings in the tests/ directory to avoid mock credentials false positives
            if "tests" in filepath.replace("\\", "/").lower() or "test_" in os.path.basename(filepath).lower():
                continue
                
            # Gating rule: Block commit if there is any High or Medium security issue
            if "高" in severity or "High" in severity or "中" in severity or "Medium" in severity:
                security_passed = False
                actual_security_findings.append(finding_data)
                
    # 3. Aggregate results and write marker JSON
    status_dir = os.path.join(workspace_path, ".agents", "status")
    os.makedirs(status_dir, exist_ok=True)
    status_file = os.path.join(status_dir, "quality_passed.json")
    
    overall_passed = comment_passed and security_passed
    
    status_data = {
        "status": "passed" if overall_passed else "failed",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "comment_ratio": f"{comment_ratio:.2f}%",
        "comment_passed": comment_passed,
        "security_passed": security_passed,
        "security_issues_count": len(actual_security_findings),
        "security_findings": actual_security_findings
    }
    
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)
        
    print("--------------------------------------------------")
    print(f"质量审查完成。报告状态: {'🟢 通过 (PASSED)' if overall_passed else '🔴 拦截 (FAILED)'}")
    print(f"* 后端注释率: {comment_ratio:.2f}% ({'🟢 达标' if comment_passed else '🔴 未达标'})")
    print(f"* 阻断级安全漏洞数量: {len(actual_security_findings)} ({'🟢 安全' if security_passed else '🔴 存在风险'})")
    if actual_security_findings:
        for f in actual_security_findings:
            print(f"  - 漏洞文件: {f.get('FILE')}:{f.get('LINE')} | 严重度: {f.get('SEVERITY')} | {f.get('DESC')}")
    print("--------------------------------------------------")
    
    if not overall_passed:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run_quality_audit.py <workspace_path> <target_path>")
        sys.exit(1)
    run_quality_audit(sys.argv[1], sys.argv[2])
