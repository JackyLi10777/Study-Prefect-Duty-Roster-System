import pathlib, py_compile

# Roster: lines after def _apply_leave() at indent 20 should be at 24
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")
# Indent body of _apply_leave
in_func = False
for i in range(len(lines)):
    stripped = lines[i].strip()
    if stripped == "def _apply_leave():":
        in_func = True
        continue
    if in_func:
        if stripped == "":
            continue
        cur_indent = len(lines[i]) - len(lines[i].lstrip())
        if cur_indent <= 20 and stripped != "":
            in_func = False  # end of function
        elif cur_indent == 20:
            lines[i] = "    " + lines[i]  # add 4 spaces

c = "\n".join(lines)
p.write_text(c, "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")
    # Show around the error
    import re as re2
    m = re2.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        for offset in range(-2, 3):
            idx = ln + offset - 1
            if 0 <= idx < len(lines):
                sp = len(lines[idx]) - len(lines[idx].lstrip())
                print(f"  L{idx+1} (indent={sp}): {lines[idx][:120]}")

# Prefects: fix line 392 extra )
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Fix: .props("color=teal-7")) -> .props("color=teal-7")
c2 = c2.replace('.props("color=teal-7"))\n', '.props("color=teal-7")\n')
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")

# Verify
print()
for fpath in [
    r"D:\code_v2\app\pages\dashboard.py",
    r"D:\code_v2\app\pages\roster.py",
    r"D:\code_v2\app\pages\prefects.py",
]:
    try:
        py_compile.compile(fpath, doraise=True)
        print(f"  OK: {pathlib.Path(fpath).name}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {pathlib.Path(fpath).name}")
