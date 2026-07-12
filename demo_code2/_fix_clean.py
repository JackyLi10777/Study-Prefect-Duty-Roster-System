import pathlib, re, py_compile

def fix_corrupted_t(content):
    """Fix all corrupted _t() patterns: extra parens and triple nesting"""
    # Fix 1: _t("zh", "en"))) -> _t("zh", "en")
    content = re.sub(r'_t\(("[^"]*"),\s*("[^"]*")\)\)\)(\s*\))', r'_t(\1, \2)\3', content)
    content = re.sub(r'_t\(("[^"]*"),\s*("[^"]*")\)\)\)', r'_t(\1, \2)', content)
    
    # Fix 2: Remove double )) after _t() calls
    content = re.sub(r'_t\(("[^"]*")\s*,\s*("[^"]*")\)\)', r'_t(\1, \2)', content)
    
    # Fix 3: Triple-nested _t
    content = re.sub(r'_t\(("[^"]*"),\s*_t\(("[^"]*"),\s*_t\(("[^"]*"),\s*("[^"]*")\)\)\)', r'_t(\1, \4)', content)
    
    # Fix 4: Double-nested _t
    content = re.sub(r'_t\(("[^"]*"),\s*_t\(("[^"]*"),\s*("[^"]*")\)\)', r'_t(\1, \3)', content)
    
    return content

for fname in ["roster.py", "prefects.py", "dashboard.py"]:
    p = pathlib.Path(r"D:\code_v2\app\pages") / fname
    c = p.read_text("utf-8")
    c = fix_corrupted_t(c)
    p.write_text(c, "utf-8")
    try:
        py_compile.compile(str(p), doraise=True)
        print(f"{fname} SYNTAX OK")
    except py_compile.PyCompileError as e:
        print(f"{fname} SYNTAX ERROR: {str(e)[:200]}")
        # Show the problematic line
        lines = c.split("\n")
        # Extract line number from error
        import re as re2
        m = re2.search(r'line (\d+)', str(e))
        if m:
            ln = int(m.group(1))
            for offset in range(-2, 3):
                idx = ln + offset - 1
                if 0 <= idx < len(lines):
                    print(f"  L{idx+1}: {lines[idx][:150]}")

for fname in ["main.py", "sidebar.py"]:
    try:
        p = pathlib.Path(r"D:\code_v2\app") / fname if fname == "main.py" else pathlib.Path(r"D:\code_v2\app\components") / fname
        py_compile.compile(str(p), doraise=True)
        print(f"{fname} SYNTAX OK")
    except py_compile.PyCompileError as e:
        print(f"{fname} SYNTAX ERROR: {str(e)[:200]}")

try:
    py_compile.compile(str(pathlib.Path(r"D:\code_v2\app\theme.py")), doraise=True)
    print("theme.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"theme.py SYNTAX ERROR: {str(e)[:200]}")
    
try:
    py_compile.compile(str(pathlib.Path(r"D:\code_v2\app\pages\audit.py")), doraise=True)
    print("audit.py SYNTAX OK")
except py_compile.PyCompileError as e:
    print(f"audit.py SYNTAX ERROR: {str(e)[:200]}")
