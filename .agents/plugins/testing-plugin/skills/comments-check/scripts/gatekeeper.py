import os
import sys
import json
import subprocess
from datetime import datetime

def check_marker_file(filepath: str, max_age_seconds: int = 300) -> tuple:
    if not os.path.exists(filepath):
        return False, "标记文件不存在"
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        status = data.get("status")
        timestamp_str = data.get("timestamp")
        
        if status != "passed":
            return False, f"状态校验未通过 (status: {status})"
            
        # Parse timestamp to verify age
        marker_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        age = (datetime.now() - marker_time).total_seconds()
        
        if age > max_age_seconds:
            return False, f"标记文件已过期 (生成于 {timestamp_str}，距今 {int(age)} 秒前，要求 5 分钟内)"
            
        return True, "通过"
    except Exception as e:
        return False, f"解析标记文件异常: {str(e)}"

def run_gatekeeper(workspace_path: str, commit_message: str = ""):
    os.chdir(workspace_path)
    
    test_marker = os.path.join(workspace_path, ".agents", "status", "test_passed.json")
    quality_marker = os.path.join(workspace_path, ".agents", "status", "quality_passed.json")
    
    print("==================================================")
    print("🔒 Git Commit Quality Gatekeeper (Git 提交质量守卫)")
    print("==================================================")
    
    # 1. Check unit test status
    test_ok, test_msg = check_marker_file(test_marker)
    print(f"* 单元测试检查: {'🟢 OK' if test_ok else '🔴 FAILED'} ({test_msg})")
    
    # 2. Check code quality status
    quality_ok, quality_msg = check_marker_file(quality_marker)
    print(f"* 代码质量检查: {'🟢 OK' if quality_ok else '🔴 FAILED'} ({quality_msg})")
    
    print("--------------------------------------------------")
    
    if not (test_ok and quality_ok):
        print("❌ 门禁拦截: 单元测试或质量检查未通过或已过期。")
        print("   - 请先运行单元测试及质量审计以刷新状态标记。")
        print("   - 操作已被中止，拒绝提交。")
        print("==================================================")
        sys.exit(1)
        
    print("🟢 门禁放行: 所有检查通过且在时效范围内，允许提交！")
    print("==================================================")
    
    # 3. Trigger git-save skill script
    git_save_script = os.path.join(workspace_path, ".agents", "plugins", "testing-plugin", "skills", "git-save", "scripts", "git-save.ps1")
    
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", git_save_script]
    if commit_message:
        cmd.append(commit_message)
        
    print(f"执行存档提交中...")
    result = subprocess.run(cmd, capture_output=False)
    sys.exit(result.returncode)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gatekeeper.py <workspace_path> [commit_message]")
        sys.exit(1)
        
    msg = sys.argv[2] if len(sys.argv) > 2 else ""
    run_gatekeeper(sys.argv[1], msg)
