import pathlib, py_compile, subprocess
p = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
lines = p.read_text("utf-8").split("\n")
# Remove trailing extra ) on these 4 lines
for idx in [322, 326, 331, 336]:
    if idx < len(lines) and lines[idx].endswith("))"):
        lines[idx] = lines[idx][:-1]  # remove last )
        print(f"Fixed line {idx+1}")
p.write_text("\n".join(lines), "utf-8")
py_compile.compile(str(p), doraise=True)
print("Syntax OK")
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
