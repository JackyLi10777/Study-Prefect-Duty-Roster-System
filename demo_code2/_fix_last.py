import pathlib, py_compile

# roster.py: line 111 has 16 spaces, needs 20 to be inside the with block
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")

# Fix line 111: add 4 spaces at the beginning
# Line 111 is index 110 (0-based)
old_l111 = lines[110]
lines[110] = "    " + old_l111
c = "\n".join(lines)
p.write_text(c, "utf-8")

try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

# Fix prefects.py line 126 - corrupted dict entry
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Fix the double _t and missing parens in the STANDARD_FIELDS dict
c2 = c2.replace(
    '"_t("\\u6d3b\\u8e8d", _t("\\u6d3b\\u8e8d", "Active"), "zh":',
    '"_t("\\u6d3b\\u8e8d", "Active"), "zh":'
)
# Or actual chars version
c2 = c2.replace(
    '_t("\u6d3b\u8e8d", _t("\u6d3b\u8e8d", "Active"), "zh":',
    '_t("\u6d3b\u8e8d", "Active"), "zh":'
)
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")
    # Show lines around 116-130
    lines2 = c2.split("\n")
    for i in range(115, min(130, len(lines2))):
        print(f"  L{i+1}: {lines2[i][:150]}")

# Final check
print("\n=== FINAL ===")
for fpath in [
    r"D:\code_v2\app\pages\dashboard.py",
    r"D:\code_v2\app\pages\roster.py",
    r"D:\code_v2\app\pages\prefects.py",
]:
    try:
        py_compile.compile(fpath, doraise=True)
        print(f"  OK: {pathlib.Path(fpath).name}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {pathlib.Path(fpath).name}: {str(e)[:150]}")
