import pathlib, py_compile

# FIX prefects.py: missing ) before on_click
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Pattern: _t("X", "Y", on_click= -> _t("X", "Y"), on_click=
c2 = c2.replace('_t("\u53d6\u6d88", "Cancel", on_click=edit_dialog.close)', '_t("\u53d6\u6d88", "Cancel"), on_click=edit_dialog.close)')
c2 = c2.replace('_t("\u4fdd\u5b58", "Save", on_click=lambda: _save_prefect())', '_t("\u4fdd\u5b58", "Save"), on_click=lambda: _save_prefect())')
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")

# FIX roster.py: try block indentation
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")
# Line 134 (idx 133): "daily = ..." needs +4 (inside try), currently at 24 -> 28
# Line 135: "if daily:" needs +4 too
lines[133] = "    " + lines[133]
lines[134] = "    " + lines[134]
p.write_text("\n".join(lines), "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

# FINAL CHECK
print()
for f in ["app/pages/dashboard.py","app/pages/roster.py","app/pages/prefects.py",
          "app/pages/audit.py","app/pages/leave.py","app/main.py"]:
    fp = pathlib.Path(f"D:/code_v2/{f}")
    try:
        py_compile.compile(str(fp), doraise=True)
        print(f"  OK: {fp.name}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {fp.name}")
