import os
import sys
import re

def analyze_file(filepath):
    if not os.path.exists(filepath):
        print(f"错误: 文件 {filepath} 不存在。")
        sys.exit(1)
        
    ext = os.path.splitext(filepath)[1].lower()
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    total_lines = len(lines)
    blank_lines = 0
    comment_lines = 0
    code_lines = 0
    
    in_block_comment = False
    block_quote_char = None  # For Python docstrings (triple double or single quotes)
    
    missing_comment_items = []
    
    for idx, line in enumerate(lines):
        stripped = line.strip()
        line_num = idx + 1
        
        if not stripped:
            blank_lines += 1
            continue
            
        # Check Python comment rules
        if ext == '.py':
            # Check triple quotes for docstrings
            if not in_block_comment:
                if stripped.startswith('"""'):
                    comment_lines += 1
                    if stripped.endswith('"""') and len(stripped) > 3 and stripped.count('"""') == 2:
                        # Single line docstring
                        pass
                    else:
                        in_block_comment = True
                        block_quote_char = '"""'
                    continue
                elif stripped.startswith("'''"):
                    comment_lines += 1
                    if stripped.endswith("'''") and len(stripped) > 3 and stripped.count("'''") == 2:
                        # Single line docstring
                        pass
                    else:
                        in_block_comment = True
                        block_quote_char = "'''"
                    continue
            else:
                comment_lines += 1
                if block_quote_char and stripped.endswith(block_quote_char):
                    in_block_comment = False
                    block_quote_char = None
                continue
                
            if stripped.startswith('#'):
                comment_lines += 1
            else:
                code_lines += 1
                # Check if this is a function or class definition
                if stripped.startswith('def ') or stripped.startswith('class '):
                    # Check if there is a docstring or comment in the next 3 lines
                    has_doc = False
                    for j in range(idx + 1, min(idx + 4, len(lines))):
                        next_stripped = lines[j].strip()
                        if not next_stripped:
                            continue
                        if next_stripped.startswith('"""') or next_stripped.startswith("'''") or next_stripped.startswith('#'):
                            has_doc = True
                            break
                        # If we see another def/class or non-indent, stop
                        if next_stripped.startswith('def ') or next_stripped.startswith('class '):
                            break
                    if not has_doc:
                        item_name = re.split(r'[(:]', stripped)[0].strip()
                        missing_comment_items.append((line_num, item_name))
                        
        # Check JS/TS/CSS comment rules
        elif ext in ['.js', '.ts', '.tsx', '.jsx', '.css', '.java', '.go']:
            if not in_block_comment:
                if stripped.startswith('/*'):
                    comment_lines += 1
                    if stripped.endswith('*/') and len(stripped) > 2:
                        pass
                    else:
                        in_block_comment = True
                    continue
            else:
                comment_lines += 1
                if stripped.endswith('*/'):
                    in_block_comment = False
                continue
                
            if stripped.startswith('//'):
                comment_lines += 1
            else:
                code_lines += 1
                # Check for JS/TS function or class definition
                is_def = False
                if stripped.startswith('class ') or stripped.startswith('export class '):
                    is_def = True
                elif stripped.startswith('function ') or stripped.startswith('export function ') or stripped.startswith('const ') and '=>' in stripped:
                    is_def = True
                    
                if is_def:
                    # Check if there is a comment above it (prev 3 lines) or doc comment
                    has_doc = False
                    for j in range(max(0, idx - 3), idx):
                        prev_stripped = lines[j].strip()
                        if prev_stripped.startswith('//') or prev_stripped.startswith('/*') or prev_stripped.endswith('*/'):
                            has_doc = True
                            break
                    if not has_doc:
                        item_name = re.split(r'[{(=]', stripped)[0].strip()
                        missing_comment_items.append((line_num, item_name))
        else:
            # Fallback check
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*') or stripped.endswith('*/'):
                comment_lines += 1
            else:
                code_lines += 1
                
    return {
        "filepath": filepath,
        "total_lines": total_lines,
        "blank_lines": blank_lines,
        "comment_lines": comment_lines,
        "code_lines": code_lines,
        "missing_items": missing_comment_items
    }

def main():
    if len(sys.argv) < 2:
        print("用法: python check_comments.py <file_or_dir_path>")
        sys.exit(1)
        
    target = sys.argv[1]
    
    files_to_analyze = []
    if os.path.isfile(target):
        files_to_analyze.append(target)
    elif os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            # Ignore standard paths
            if any(p in root for p in ['.venv', 'node_modules', '.git', '__pycache__', 'dist', 'build']):
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.py', '.js', '.ts', '.tsx', '.css']:
                    files_to_analyze.append(os.path.join(root, file))
    else:
        print(f"错误: 目标 {target} 不存在。")
        sys.exit(1)
        
    global_total_lines = 0
    global_blank_lines = 0
    global_comment_lines = 0
    global_code_lines = 0
    global_missing_items = []
    
    print(f"AUDIT_TARGET:{target}")
    print(f"FILES_COUNT:{len(files_to_analyze)}")
    
    for filepath in files_to_analyze:
        stats = analyze_file(filepath)
        if not stats:
            continue
            
        global_total_lines += stats['total_lines']
        global_blank_lines += stats['blank_lines']
        global_comment_lines += stats['comment_lines']
        global_code_lines += stats['code_lines']
        
        # Format: filepath|line_num|name
        for line_num, name in stats['missing_items']:
            global_missing_items.append((filepath, line_num, name))
            
    print(f"TOTAL_LINES:{global_total_lines}")
    print(f"BLANK_LINES:{global_blank_lines}")
    print(f"COMMENT_LINES:{global_comment_lines}")
    print(f"CODE_LINES:{global_code_lines}")
    
    ratio = (global_comment_lines / global_code_lines * 100) if global_code_lines > 0 else 0
    print(f"COMMENT_RATIO:{ratio:.2f}%")
    
    required_ratio = 11.11
    passed_density = ratio >= required_ratio
    print(f"DENSITY_CHECK:{'PASSED' if passed_density else 'FAILED'}")
    
    print("MISSING_ITEMS_START")
    for filepath, line_num, name in global_missing_items:
        print(f"{filepath}|{line_num}|{name}")
    print("MISSING_ITEMS_END")

if __name__ == '__main__':
    main()
