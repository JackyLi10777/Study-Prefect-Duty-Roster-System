import pathlib, re, py_compile

def balance_line(line):
    """Fix a single line with unbalanced _t() parentheses."""
    # Count all ( and ) 
    opens = line.count("(")
    closes = line.count(")")
    
    if opens == closes:
        return line
    
    diff = opens - closes
    if diff > 0:
        # Missing closing parens - add them before any trailing code
        # Find the last place where a ) would be expected
        # Add closing parens before .classes, .props, , or end of logical expression
        line = line + (")" * diff)
    elif diff < 0:
        # Too many closing parens - remove extras from the end
        # Find double/triple ))) and collapse
        while line.count("))"):
            line = line.replace(")))", ")")
            line = line.replace("))", ")")
    return line

for fname in ["roster.py", "prefects.py", "dashboard.py"]:
    p = pathlib.Path(r"D:\code_v2\app\pages") / fname
    c = p.read_text("utf-8")
    
    # First pass: fix specific known corrupted patterns
    # Pattern: _t("...", _t("...", "..."))) -> _t("...", "...")
    for _ in range(3):
        c = re.sub(r'_t\("([^"]*)"\s*,\s*_t\("[^"]*"\s*,\s*"([^"]*)"\)\)', r'_t("\1", "\2")', c)
    
    # Pattern: _t("...", "..."))).class -> _t("...", "...")).class
    c = re.sub(r'_t\(("[^"]*")\s*,\s*("[^"]*")\)\)\)', r'_t(\1, \2))', c)
    
    # Pattern: _t("...", "..."))  (double close) -> _t("...", "...")
    c = re.sub(r'_t\(("[^"]*")\s*,\s*("[^"]*")\)\)(?!\))', r'_t(\1, \2)', c)
    
    # Fix line by line paren balancing
    lines = c.split("\n")
    fixed_lines = []
    for line in lines:
        if "_t(" in line:
            fixed_lines.append(balance_line(line))
        else:
            fixed_lines.append(line)
    c = "\n".join(fixed_lines)
    
    p.write_text(c, "utf-8")
    
    try:
        py_compile.compile(str(p), doraise=True)
        print(f"{fname} SYNTAX OK!")
    except py_compile.PyCompileError as e:
        print(f"{fname} SYNTAX ERROR: {e}")
        # Show lines with _t that still have issues
        lines = c.split("\n")
        for i, line in enumerate(lines):
            if "_t(" in line and line.count("(") != line.count(")"):
                print(f"  L{i+1}: opens={line.count('(')} closes={line.count(')')} {line[:120]}")
