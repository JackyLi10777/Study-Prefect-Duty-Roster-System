import pathlib, re, py_compile, subprocess

def fix_all():
    files = [
        r"D:\code_v2\app\pages\dashboard.py",
        r"D:\code_v2\app\pages\prefects.py",
        r"D:\code_v2\app\pages\roster.py",
        r"D:\code_v2\app\pages\audit.py",
        r"D:\code_v2\app\pages\leave.py",
        r"D:\code_v2\app\main.py",
    ]
    fixed = 0
    for fp in files:
        p = pathlib.Path(fp)
        if not p.exists():
            continue
        lines = p.read_text("utf-8").split("\n")
        new_lines = []
        for i, line in enumerate(lines):
            new_line = line
            if "_t(" in line and ")." in line and "ui." in line:
                new_line = re.sub(
                    r"(ui\.\w+)\((_t\([^)]*\)[^)]*)\.(classes|props|style|on)(\([^)]*\))\)",
                    r"\1(\2).\3\4",
                    line,
                )
                if new_line != line:
                    fixed += 1
            new_lines.append(new_line)
        if new_lines != lines:
            p.write_text("\n".join(new_lines), "utf-8")
    print(f"Fixed {fixed} lines")
    for fp in files:
        p = pathlib.Path(fp)
        if not p.exists(): continue
        try:
            py_compile.compile(str(p), doraise=True)
            print(f"  OK: {p.name}")
        except py_compile.PyCompileError as e:
            print(f"  FAIL: {p.name} - {e}")
    r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
    passed = "52 passed" in r.stdout + r.stderr
    print(f"Tests: {'52/52' if passed else 'FAILED'}")

if __name__ == "__main__":
    fix_all()
