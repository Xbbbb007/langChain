import os
import sys
import re

# Regex patterns for detecting hardcoded secrets/credentials
SECRET_PATTERNS = [
    (r'(?i)(api_key|apikey|secret_key|secret|password|passwd|private_key|token|jwt_secret)\s*[:=]\s*[\'"][^\'"]+[\'"]', "可能存在硬编码密钥或密码"),
    (r'sk-[a-zA-Z0-9]{48}', "通义千问或 OpenAI API Key 格式匹配"),
    (r'Bearer\s+[a-zA-Z0-9_\-\.]{20,}', "明文承载令牌 (Bearer Token)"),
]

# Patterns for SQL injection vulnerabilities
SQL_INJECTION_PATTERNS = [
    (r'\.execute\(\s*f["\']', "SQL 执行中使用 f-string 插值，具有 SQL 注入风险"),
    (r'\.execute\(\s*["\'].*?\%.*?["\']\s*%', "SQL 执行中使用 % 格式化，具有 SQL 注入风险"),
    (r'\.execute\(\s*["\'].*?\{\}.*?["\']\.format', "SQL 执行中使用 .format() 格式化，具有 SQL 注入风险"),
]

# Unsafe python functions
UNSAFE_FUNCTIONS = [
    (r'\beval\(', "使用了 eval() 函数，可能导致任意代码执行漏洞"),
    (r'\bexec\(', "使用了 exec() 函数，可能导致任意代码执行漏洞"),
    (r'\bos\.system\(', "使用了 os.system()，存在系统命令注入风险"),
    (r'\bsubprocess\.Popen\(\s*.*?shell\s*=\s*True', "使用了 shell=True 的 subprocess 调用，存在命令注入风险"),
]

# Unsafe CORS configuration
UNSAFE_CORS = [
    (r'allow_origins\s*=\s*\[\s*["\']\*["\']\s*\]\s*,\s*allow_credentials\s*=\s*True', "FastAPI 允许了所有源跨域，且开启了凭证支持，存在安全风险"),
]

def audit_file(filepath):
    if not os.path.exists(filepath):
        print(f"错误: 文件 {filepath} 不存在。")
        return []

    ext = os.path.splitext(filepath)[1].lower()
    basename = os.path.basename(filepath)

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    findings = []

    for idx, line in enumerate(lines):
        line_num = idx + 1
        stripped = line.strip()

        # Skip comment lines for code vulnerability checks, but NOT for credential checks
        is_comment = stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*') or stripped.endswith('*/')

        # 1. Check for plaintext secrets (both code and comments/config files)
        # Avoid matching env variables like os.getenv("SECRET")
        if not re.search(r'getenv|environ|get_env|os\.env', line):
            for pattern, desc in SECRET_PATTERNS:
                if re.search(pattern, stripped):
                    # Check if it looks like a placeholder like "YOUR_API_KEY" or "admin" (exclude default admin password from being flagged as a real leak if it's mock)
                    if "YOUR_" not in stripped.upper() and "PLACEHOLDER" not in stripped.upper():
                        findings.append({
                            "line": line_num,
                            "type": "敏感信息泄露",
                            "severity": "高 (High)",
                            "description": desc,
                            "code": stripped[:100]
                        })
                        break

        # If it's a code comment, don't run code logic vulnerability checks
        if is_comment:
            continue

        # 2. Check for SQL Injection risks (mostly in python/js files)
        if ext in ['.py', '.js', '.ts', '.tsx']:
            for pattern, desc in SQL_INJECTION_PATTERNS:
                if re.search(pattern, stripped):
                    findings.append({
                        "line": line_num,
                        "type": "SQL 注入隐患",
                        "severity": "高 (High)",
                        "description": desc,
                        "code": stripped[:100]
                    })
                    break

        # 3. Check for Unsafe Functions (in Python files)
        if ext == '.py':
            for pattern, desc in UNSAFE_FUNCTIONS:
                if re.search(pattern, stripped):
                    findings.append({
                        "line": line_num,
                        "type": "代码执行隐患",
                        "severity": "中 (Medium)",
                        "description": desc,
                        "code": stripped[:100]
                    })
                    break

        # 4. Check for FastAPI unsafe CORS configs
        if basename == 'main.py' or ext == '.py':
            for pattern, desc in UNSAFE_CORS:
                if re.search(pattern, stripped):
                    findings.append({
                        "line": line_num,
                        "type": "跨域配置漏洞",
                        "severity": "中 (Medium)",
                        "description": desc,
                        "code": stripped[:100]
                    })
                    break

    # If it is a config file like .env, check if there are raw values that are not placeholders
    if ext == '.env' or basename == '.env':
        for idx, line in enumerate(lines):
            line_num = idx + 1
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                key, val = stripped.split('=', 1)
                val = val.strip().strip('"').strip("'")
                # Flag if value is not a placeholder, is not empty, and looks sensitive
                if val and not val.startswith('<') and not val.endswith('>') and len(val) > 5:
                    if any(k in key.lower() for k in ['secret', 'key', 'password', 'token']):
                        findings.append({
                            "line": line_num,
                            "type": "配置文件明文漏洞",
                            "severity": "高 (High)",
                            "description": f"配置文件键 {key} 包含明文敏感信息",
                            "code": f"{key}=******"
                        })

    return findings

def main():
    if len(sys.argv) < 2:
        print("用法: python run_audit.py <file_or_directory_path>")
        sys.exit(1)

    target = sys.argv[1]
    
    all_findings = []

    if os.path.isfile(target):
        all_findings = audit_file(target)
    elif os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            # Ignore virtual environment, agents configs, and standard excludes
            if any(p in root for p in ['.venv', '.agents', 'node_modules', '.git', '__pycache__', 'dist', 'build']):
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.py', '.js', '.ts', '.tsx', '.json', '.env', '.yaml', '.yml']:
                    filepath = os.path.join(root, file)
                    file_findings = audit_file(filepath)
                    for f in file_findings:
                        f['file'] = filepath
                    all_findings.extend(file_findings)
    else:
        print(f"错误: 目标路径 {target} 既不是文件也不是目录。")
        sys.exit(1)

    print(f"AUDIT_TARGET:{target}")
    print(f"FINDINGS_COUNT:{len(all_findings)}")
    print("FINDINGS_START")
    for f in all_findings:
        file_info = f.get('file', target)
        print(f"FILE:{file_info}|LINE:{f['line']}|TYPE:{f['type']}|SEVERITY:{f['severity']}|DESC:{f['description']}|CODE:{f['code']}")
    print("FINDINGS_END")

if __name__ == '__main__':
    main()
