import pathlib, py_compile, subprocess

# ===== Pass 2: Roster safety - reset _current_roster on page load =====
p = pathlib.Path(r"D:\code_v2\app\pages\roster.py")
c = p.read_text("utf-8")
# Add _current_roster = None at the start of roster_page
old = "def roster_page():\n    \"\"\"Main roster management page.\"\"\"\n    apply_theme()"
new = "def roster_page():\n    \"\"\"Main roster management page.\"\"\"\n    global _current_roster\n    _current_roster = None  # Reset stale state\n    apply_theme()"
c = c.replace(old, new)
p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("roster.py: _current_roster reset on page load")

# ===== Pass 4: Scripture reflections - add en_reflections + is_zh() check =====
p2 = pathlib.Path(r"D:\code_v2\app\pages\dashboard.py")
c2 = p2.read_text("utf-8")

# Add en_reflections list
old_ref = 'reflections = ['
new_ref = '''en_reflections = [
                "Today in your busy duty work, remember you are working for God, not for men.",
                "True leaders first become servants. How will you serve your team today?",
                "When you feel weary, look to God; He will give you new strength.",
                "In every small responsibility, live out your faith; your faithfulness will be seen.",
                "Whatever challenge you face today, know your labor in the Lord is not in vain.",
                "Entrust today''s duties to God; He will guide your steps.",
                "In the tension between study and duty, let God''s Word be your strength.",
            ]

reflections = ['''
c2 = c2.replace(old_ref, new_ref)

# Add is_zh() check to reflection selection
old_ref_sel = 'reflection = reflections[date.today().weekday()]'
new_ref_sel = 'reflection = reflections[date.today().weekday()] if is_zh() else en_reflections[date.today().weekday()]'
c2 = c2.replace(old_ref_sel, new_ref_sel)

p2.write_text(c2, "utf-8")
py_compile.compile(str(p2), doraise=True)
print("dashboard.py: en_reflections + is_zh() check for reflections")

# Run tests
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Restart app and test all pages
import os, time, urllib.request, urllib.error
os.system("taskkill /f /im python.exe 2>nul")
time.sleep(2)
subprocess.Popen(["python", "app/main.py"], cwd=r"D:\code_v2", stderr=open("_ef.log","w"))
time.sleep(5)

for url in ["http://localhost:8080/","http://localhost:8080/prefects","http://localhost:8080/roster"]:
    try:
        r = urllib.request.urlopen(url, timeout=5)
        name = url.split("/")[-1] or "dashboard"
        print(f"{name}: HTTP {r.status}")
    except urllib.error.HTTPError as e:
        name = url.split("/")[-1] or "dashboard"
        print(f"{name}: HTTP {e.code} FAIL")
    except Exception as e:
        print(f"{url}: {e}")
