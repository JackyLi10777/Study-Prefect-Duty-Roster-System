import pathlib, py_compile

# FIX roster.py
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
lines = p.read_text("utf-8").split("\n")
lines[122] = "    " + lines[122]  # if body: +4
lines[123] = "    " + lines[123]  # ui.notify: +4 more
p.write_text("\n".join(lines), "utf-8")
try:
    py_compile.compile(str(p), doraise=True)
    print("roster.py OK!")
except py_compile.PyCompileError as e:
    print(f"roster.py: {e}")

# FIX prefects.py
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
# Fix missing ) in _t calls
c2 = c2.replace(
    '_t("\u53d6\u6d88", "\u53d6\u6d88", on_click=edit_dialog.close)',
    '_t("\u53d6\u6d88", "Cancel"), on_click=edit_dialog.close)'
)
c2 = c2.replace(
    '_t("\u4fdd\u5b58", "\u4fdd\u5b58", on_click=lambda: _save_prefect())',
    '_t("\u4fdd\u5b58", "Save"), on_click=lambda: _save_prefect())'
)
p2.write_text(c2, "utf-8")
try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK!")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")

# VERIFY
for f in ["app/pages/dashboard.py","app/pages/roster.py","app/pages/prefects.py",
          "app/pages/audit.py","app/pages/leave.py","app/main.py"]:
    fp = pathlib.Path(f"D:/code_v2/{f}")
    try:
        py_compile.compile(str(fp), doraise=True)
        print(f"  OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {f}")
