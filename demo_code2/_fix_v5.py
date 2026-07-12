import pathlib, py_compile

# ROSTER: lines 135-137 are over-indented (32sp instead of 28)
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")
for i in [134, 135, 136]:
    if i < len(lines) and lines[i].startswith("    "):
        lines[i] = lines[i][4:]  # remove 4 spaces
        print(f"Unindented L{i+1}")
p.write_text("\n".join(lines), "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

# PREFECTS: line 481 lambda list missing closing bracket
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Fix: lambda: [)  -> lambda: [])  (add missing ] after the actions)
# But first check what the line looks like
lines2 = c2.split("\n")
if len(lines2) > 480:
    print(f"L481: {lines2[480][:200]}")
    print(f"L482: {lines2[481][:200] if len(lines2) > 481 else 'N/A'}")
    print(f"L483: {lines2[482][:200] if len(lines2) > 482 else 'N/A'}")
p2.write_text(c2, "utf-8")
