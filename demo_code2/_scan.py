import pathlib, re

print("=== JTBD/ODI PROJECT SCAN ===\n")

issues = []

# 1. Hardcoded English
for name in ["dashboard","roster","prefects","audit","leave"]:
    c = pathlib.Path(f"app/pages/{name}.py").read_text("utf-8")
    en_labels = len(re.findall(r"ui\.label\(" + chr(34) + r"[A-Z][^" + chr(34) + r"]+" + chr(34), c))
    en_buttons = len(re.findall(r"ui\.button\(" + chr(34) + r"[A-Z][^" + chr(34) + r"]+" + chr(34), c))
    total = en_labels + en_buttons
    if total > 0:
        issues.append((f"{name}: {total} EN labels/buttons", "MED", total))

# 2. Bare excepts
for name in ["dashboard","roster","prefects","audit","leave"]:
    c = pathlib.Path(f"app/pages/{name}.py").read_text("utf-8")
    bare = len(re.findall(r"except\s*:", c))
    if bare > 0:
        issues.append((f"{name}: {bare} bare except", "HIGH", bare))

# 3. Module-level globals
for name in ["roster","prefects","dashboard"]:
    c = pathlib.Path(f"app/pages/{name}.py").read_text("utf-8")
    globals_count = len(re.findall(r"^[a-z_]+\s*=\s*(None|\[\]|\{\})", c, re.MULTILINE))
    if globals_count > 0:
        issues.append((f"{name}: {globals_count} module globals", "HIGH", globals_count))

# 4. Missing docstrings
for name in ["dashboard","roster","prefects","audit","leave"]:
    c = pathlib.Path(f"app/pages/{name}.py").read_text("utf-8")
    funcs = re.findall(r"^def (\w+)", c, re.MULTILINE)
    missing = sum(1 for fn in funcs if not c[c.find(f"def {fn}"):].split("\n")[1].strip().startswith(chr(34)+chr(34)+chr(34)))
    if missing > 0:
        issues.append((f"{name}: {missing}/{len(funcs)} missing docstrings", "LOW", missing))

# Print findings
for issue, sev, count in sorted(issues, key=lambda x: (x[1], -x[2])):
    print(f"[{sev}] {issue}")

print(f"\nTotal systemic issues: {len(issues)}")

# Check app responsiveness
import urllib.request
try:
    r = urllib.request.urlopen("http://localhost:8080/", timeout=5)
    print(f"\nApp status: HTTP {r.status}")
except:
    print("\nApp status: NOT RUNNING")
