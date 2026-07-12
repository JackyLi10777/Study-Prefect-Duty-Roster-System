import pathlib, re, py_compile, subprocess

def fix_chaining(content: str) -> str:
    """Fix _t().classes() -> wrap correctly around ui.xxx()"""
    # Pattern: ui.label(_t(X, Y).classes(Z)) -> ui.label(_t(X, Y)).classes(Z)
    # This handles both simple and nested _t() patterns
    # Strategy: find ui.xxx(_t( ... ).classes( and move the ) before .classes
    
    # Fix 1: ui.xxx(_t(a, b).classes(c)) -> ui.xxx(_t(a, b)).classes(c)
    # For simple case where _t has 2 string args
    content = re.sub(
        r'(ui\.\w+)\((_t\("[^"]*",\s*"[^"]*")\)\.(classes|props|style|on)(\([^)]+\))\)',
        r'\1(\2).\3\4',
        content
    )
    
    # Fix 2: Nested _t like ui.label(_t(A, _t(B, C).classes(D)))
    # First, extract the inner _t without .classes
    # _t(A, _t(B, C)).classes(D) is what we want
    # Current: _t(A, _t(B, C).classes(D))
    # This is tricky with regex alone, handle manually
    
    return content

def fix_chaining_manual(content: str) -> str:
    """Manual fixes for specific known patterns"""
    # dashboard.py line 180
    content = content.replace(
        'ui.label(_t("\u6bcf\u65e5\u91d1\u53e5\u3001\u7cfb\u7edf\u72b6\u6001\u3001KPI\u6982\u89c8\u3001\u5907\u4efd\u4e0e\u8fd8\u539f", "Daily scripture, system status, KPI overview, backup & restore.").classes(',
        'ui.label(_t("\u6bcf\u65e5\u91d1\u53e5\u3001\u7cfb\u7edf\u72b6\u6001\u3001KPI\u6982\u89c8\u3001\u5907\u4efd\u4e0e\u8fd8\u539f", "Daily scripture, system status, KPI overview, backup & restore.")).classes('
    )
    
    # Simple pattern: ui.label(_t("X", "Y").classes("Z")) -> ui.label(_t("X", "Y")).classes("Z")
    # Use a more robust regex
    content = re.sub(
        r'ui\.(label|button)\(_t\("([^"]*)",\s*"([^"]*)"\)\.(classes|props)(\([^)]+\))\)',
        r'ui.\1(_t("\2", "\3")).\4\5',
        content
    )
    
    # Fix nested _t patterns: _t("A", _t("B", "C").classes("D")) 
    # -> _t("A", _t("B", "C")).classes("D")
    content = re.sub(
        r'_t\("([^"]*)",\s*_t\("([^"]*)",\s*"([^"]*)"\)\.(classes|props)(\([^)]+\))\)',
        r'_t("\1", _t("\2", "\3")).\4\5',
        content
    )
    
    return content

# Fix all affected files
affected = ['app/pages/dashboard.py', 'app/pages/prefects.py', 'app/pages/roster.py']
count = 0

for fp in affected:
    p = pathlib.Path(r'D:\code_v2') / fp
    if not p.exists():
        continue
    c = p.read_text('utf-8')
    c_new = fix_chaining_manual(c)
    if c != c_new:
        p.write_text(c_new, 'utf-8')
        count += 1
        print(f'Fixed: {fp}')

# Re-scan after first pass
print('\nRe-scanning after fix pass 1...')
remaining = []
for fp in affected:
    p = pathlib.Path(r'D:\code_v2') / fp
    c = p.read_text('utf-8')
    lines = c.split('\n')
    for i, line in enumerate(lines, 1):
        if re.search(r'ui\.\w+\(_t\([^)]+\)\.(classes|props)\(', line):
            remaining.append((fp, i, line.strip()[:140]))
            print(f'  STILL BROKEN: {fp}:{i} -> {line.strip()[:120]}')

print(f'\nRemaining after pass 1: {len(remaining)}')
if remaining:
    # Second pass: fix remaining with more aggressive regex
    for fp in affected:
        p = pathlib.Path(r'D:\code_v2') / fp
        c = p.read_text('utf-8')
        # Fix: ui.xxx(_t(...).classes(...)) where _t args may be complex
        # Pattern: ui.xxx( _t( <anything except ")>" ) .classes( <args> ) )
        # We need to find the ) that closes _t( and move it after .classes()
        c = re.sub(
            r'(ui\.\w+)\((_t\([^)]+(?:\"[^"]*\"[^)]*)*)\)\.(classes|props)(\([^)]+\))\)',
            r'\1(\2).\3\4',
            c
        )
        p.write_text(c, 'utf-8')

# Final scan
print('\nFinal scan...')
remaining2 = 0
for fp in affected:
    p = pathlib.Path(r'D:\code_v2') / fp
    c = p.read_text('utf-8')
    lines = c.split('\n')
    for i, line in enumerate(lines, 1):
        if re.search(r'ui\.\w+\(_t\([^)]+\)\.(classes|props)\(', line):
            remaining2 += 1
            print(f'  {fp}:{i}: {line.strip()[:120]}')

print(f'Final remaining: {remaining2}')

# Verify syntax
print('\nSyntax check...')
all_ok = True
for fp in affected:
    try:
        py_compile.compile(str(pathlib.Path(r'D:\code_v2') / fp), doraise=True)
        print(f'  OK: {fp}')
    except py_compile.PyCompileError as e:
        print(f'  FAIL: {fp} - {e}')
        all_ok = False

if all_ok:
    r = subprocess.run(['python','-m','pytest','tests/','-q'], capture_output=True, text=True, cwd=r'D:\code_v2')
    print(f'\nTests: {\"52/52\" if \"52 passed\" in r.stdout+r.stderr else \"FAILED\"}')
