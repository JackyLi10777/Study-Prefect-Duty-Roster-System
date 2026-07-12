import pathlib, py_compile
p = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
lines = p.read_text("utf-8").split("\n")
# Line 98 (index 97) has 3 closing parens at end - remove one
if lines[97].endswith(")))"):
    lines[97] = lines[97][:-1]
    print("Removed extra ) from line 98")
# Also check line 341 (index 340) for same issue
if len(lines) > 341 and lines[340].endswith(")))"):
    lines[340] = lines[340][:-1]
    print("Removed extra ) from line 341")
if len(lines) > 342 and lines[341].endswith(")))"):
    lines[341] = lines[341][:-1]
    print("Removed extra ) from line 342")
if len(lines) > 383 and lines[382].endswith(")))"):
    lines[382] = lines[382][:-1]
    print("Removed extra ) from line 383")

p.write_text("\n".join(lines), "utf-8")
py_compile.compile(str(p), doraise=True)
print("prefects.py syntax OK")

import subprocess
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
