import pathlib, py_compile, subprocess

p = pathlib.Path(r"D:\code_v2\app\main.py")
c = p.read_text("utf-8")

# Add sys.excepthook after logging init
old = """    app.add_middleware(RequestIDMiddleware)

    secret = os.getenv("STORAGE_SECRET", "dev-secret-sing-yin-roster-2026")"""
new = """    app.add_middleware(RequestIDMiddleware)

    # Register sys.excepthook for exceptions outside request handling
    import sys
    def _global_excepthook(exc_type, exc_value, exc_tb):
        import traceback
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"Unhandled exception outside request context:\\n{tb_str}")
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = _global_excepthook

    secret = os.getenv("STORAGE_SECRET", "dev-secret-sing-yin-roster-2026")"""
c = c.replace(old, new)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("main.py: sys.excepthook added")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Verify
c2 = p.read_text("utf-8")
print(f"sys.excepthook present: {'sys.excepthook' in c2}")
