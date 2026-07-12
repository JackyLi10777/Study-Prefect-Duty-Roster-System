import pathlib, py_compile, subprocess

c = pathlib.Path("app/pages/dashboard.py").read_text("utf-8")
# Count items in en_reflections - count lines starting with "
en_start = c.find("en_reflections = [")
en_end = c.find("]", en_start)
en_count = c[en_start:en_end].count('"Today') + c[en_start:en_end].count('"True') + c[en_start:en_end].count('"When you') + c[en_start:en_end].count('"In every') + c[en_start:en_end].count('"Whatever') + c[en_start:en_end].count('"Entrust') + c[en_start:en_end].count('"In the tension')
zh_count = c[c.find("reflections = [", en_end):c.find("]", c.find("reflections = [", en_end))].count(chr(10))

print(f"en_reflections: {en_count} items (need 7)")
print(f"zh_reflections: {zh_count} items")

# Add missing items if needed
if en_count < 7:
    # Build complete en_reflections list
    new_en = """en_reflections = [
                "Today in your busy duty work, remember you are working for God, not for men.",
                "True leaders first become servants. How will you serve your team today?",
                "When you feel weary, look to God; He will give you new strength.",
                "In every small responsibility, live out your faith; your faithfulness will be seen.",
                "Whatever challenge you face today, know your labor in the Lord is not in vain.",
                "Entrust today\\'s duties to God; He will guide your steps.",
                "In the tension between study and duty, let God\\'s Word be your strength.",
            ]"""
    # Find old list boundaries
    old_en_end = c.find("]", en_start) + 1
    old_en = c[en_start:old_en_end]
    c = c.replace(old_en, new_en)
    pathlib.Path("app/pages/dashboard.py").write_text(c, "utf-8")
    py_compile.compile(str(pathlib.Path("D:/code_v2/app/pages/dashboard.py")), doraise=True)
    print("Added missing en_reflections items")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
