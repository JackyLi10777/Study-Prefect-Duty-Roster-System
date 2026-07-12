import pathlib, py_compile, subprocess

print("=== JTBD/ODI OPTIMIZATION ROUND ===\n")

# Fix 1: Roster bare excepts -> proper error handling
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")
c = c.replace("except:\n            pass", "except Exception:\n            pass")
c = c.replace("except:\n                pass", "except Exception:\n                pass")
# Also fix "except: pass" on single lines
c = c.replace("except: pass", "except Exception: pass")
p.write_text(c, "utf-8")
print("1. roster.py: bare excepts -> except Exception")

# Fix 2: Dashboard bare except
p2 = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c2 = p2.read_text("utf-8")
c2 = c2.replace("except: pass", "except Exception: pass")
p2.write_text(c2, "utf-8")
print("2. dashboard.py: bare excepts -> except Exception")

# Fix 3: Dashboard EN labels - wrap in _t()
# Line 209: "Uses logo.png from project folder"
c2 = c2.replace(
    '"Uses logo.png from project folder"',
    '_t("\u4f7f\u7528\u9805\u76ee\u8cc7\u6599\u593e\u4e2d\u7684 logo.png", "Uses logo.png from project folder")'
)
c2 = c2.replace(
    '"These are gentle reminders -- the system will work fine, but fixing them improves roster quality."',
    '_t("\u9019\u4e9b\u662f\u6eab\u99a8\u63d0\u793a\uff0d\uff0d\u7cfb\u7d71\u4ecd\u53ef\u6b63\u5e38\u904b\u4f5c\uff0c\u4f46\u4fee\u5fa9\u5b83\u5011\u80fd\u63d0\u5347\u503c\u73ed\u8868\u54c1\u8cea\u3002", "These are gentle reminders -- the system will work fine, but fixing them improves roster quality.")'
)
p2.write_text(c2, "utf-8")
print("3. dashboard.py: 2 EN labels wrapped in _t()")

# Verify
for f in ["app/pages/roster.py", "app/pages/dashboard.py"]:
    py_compile.compile(str(pathlib.Path(f"D:/code_v2/{f}")), doraise=True)
    print(f"   {f}: syntax OK")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
passed = "52 passed" in r.stdout + r.stderr
print(f"\nTests: {'52/52' if passed else 'FAILED'}")

# Re-scan
c3 = p.read_text("utf-8")
bare_rost = sum(1 for l in c3.split("\n") if l.strip() in ["except:", "except: pass"])
c4 = p2.read_text("utf-8")
bare_dash = sum(1 for l in c4.split("\n") if l.strip() in ["except:", "except: pass"])
print(f"Roster bare excepts remaining: {bare_rost}")
print(f"Dashboard bare excepts remaining: {bare_dash}")
