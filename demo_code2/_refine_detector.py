import pathlib

# Refine the detector to exclude CSS overrides and token definitions
script = '''"""
Dark Mode Color Leak Detector v2
Refined: ignores CSS override rules, design token definitions, and variable assignments.
Only flags actual usage of light-mode Tailwind classes in page/component code.
"""

import re
from pathlib import Path
from typing import List, Tuple

LIGHT_MODE_PATTERNS = [
    r"\\bbg-white\\b",
    r"\\bbg-slate-50\\b",
    r"\\bbg-gray-50\\b",
    r"\\btext-slate-900\\b",
    r"\\btext-black\\b",
    r"\\bborder-slate-200\\b",
    r"\\bborder-gray-300\\b",
    r"\\bshadow-sm\\b",
]

# Directories to skip entirely
SKIP_DIRS = {"__pycache__", "tests", "scripts"}

def find_leaks(root_dir: str = "app") -> List[Tuple[str, int, str]]:
    leaks = []
    root_path = Path(root_dir)

    for py_file in root_path.rglob("*.py"):
        # Skip test files and cache
        parts = set(py_file.parts)
        if parts & SKIP_DIRS:
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # Skip comments
                if stripped.startswith("#"):
                    continue
                # Skip CSS override rules (the fixes themselves)
                if "body.dark" in stripped or "!important" in stripped:
                    continue
                # Skip design token definitions (variable assignments only)
                if re.match(r"^[A-Z_]+\s*=\\s*", stripped):
                    continue
                # Skip CSS variable definitions
                if stripped.startswith("--"):
                    continue
                # Skip lines that are clearly in a CSS <style> block
                if "{{" in stripped and "}}" in stripped:
                    continue

                for pattern in LIGHT_MODE_PATTERNS:
                    if re.search(pattern, line):
                        has_dark_variant = "dark:" in line
                        if not has_dark_variant:
                            leaks.append((str(py_file), i, line.strip()[:120]))
                            break
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return leaks


def main():
    print("Scanning for Dark Mode Color Leaks (v2)...\\n")
    leaks = find_leaks()

    if not leaks:
        print("No obvious light mode color leaks detected!")
        return 0

    print(f"Found {len(leaks)} potential light mode color leaks:\\n")
    by_file = {}
    for file, line_num, content in leaks:
        by_file.setdefault(file, []).append((line_num, content))

    for file, items in sorted(by_file.items()):
        short = file.replace("app\\\\", "").replace("\\\\", "/")
        print(f"  {short}:")
        for line_num, content in items:
            print(f"    L{line_num}: {content}")
        print()

    return len(leaks)


if __name__ == "__main__":
    exit(main())
'''

pathlib.Path(r"D:\code_v2\scripts\detect_dark_mode_leaks.py").write_text(script, "utf-8")
print("Detector v2 created")

# Now add dark:shadow-sm to pages using shadow-sm
for fp, patterns in [
    (r"D:\code_v2\app\components\kpi_card.py", [("shadow-sm", "shadow-sm dark:shadow-md")]),
    (r"D:\code_v2\app\pages\audit.py", [("shadow-sm", "shadow-sm dark:shadow-md")]),
    (r"D:\code_v2\app\pages\dashboard.py", [("shadow-sm p-5", "shadow-sm dark:shadow-md p-5")]),
    (r"D:\code_v2\app\pages\leave.py", [("shadow-sm", "shadow-sm dark:shadow-md")]),
]:
    p = pathlib.Path(fp)
    c = p.read_text("utf-8")
    for old, new in patterns:
        c = c.replace(old, new)
    p.write_text(c, "utf-8")
    print(f"  Added dark:shadow to {pathlib.Path(fp).name}")

import subprocess
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"\nTests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Run detector v2
print()
import sys
sys.path.insert(0, r"D:\code_v2\scripts")
from detect_dark_mode_leaks import main as run_detector
run_detector()
