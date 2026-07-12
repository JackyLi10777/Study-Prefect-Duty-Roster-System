import pathlib

# Restore the refined v2 detector (which properly excludes CSS overrides)
script = '''"""
Dark Mode Color Leak Detector v2 (Refined)
Only flags actual page/component code, not CSS override rules or token definitions.
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

SKIP_DIRS = {"__pycache__", "tests", "scripts"}

def find_leaks(root_dir: str = "app") -> List[Tuple[str, int, str]]:
    leaks = []
    root_path = Path(root_dir)

    for py_file in root_path.rglob("*.py"):
        parts = set(py_file.parts)
        if parts & SKIP_DIRS:
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # Skip CSS override rules (the fixes themselves)
                if "body.dark" in stripped or "!important" in stripped:
                    continue
                # Skip design token definitions
                if re.match(r"^[A-Z_]+\\s*=\\s*", stripped):
                    continue
                if stripped.startswith("--"):
                    continue
                # Skip CSS blocks
                if "{{" in stripped and "}}" in stripped:
                    continue

                for pattern in LIGHT_MODE_PATTERNS:
                    if re.search(pattern, line):
                        if "dark:" not in line:
                            leaks.append((str(py_file), i, line.strip()[:120]))
                            break
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return leaks


def main():
    print("Dark Mode Color Leak Detector v2 (Refined)")
    print("=" * 50)
    leaks = find_leaks()

    if not leaks:
        print("CLEAN - zero dark mode color leaks detected!")
        return 0

    print(f"Found {len(leaks)} potential leaks:")
    by_file = {}
    for file, line_num, content in leaks:
        short = file.replace("app\\\\", "")
        by_file.setdefault(short, []).append((line_num, content))

    for file, items in sorted(by_file.items()):
        print(f"\\n  {file}:")
        for line_num, content in items:
            print(f"    L{line_num}: {content}")

    return len(leaks)


if __name__ == "__main__":
    exit(main())
'''

pathlib.Path(r"D:\code_v2\scripts\detect_dark_mode_leaks.py").write_text(script, "utf-8")
print("Refined v2 detector installed")

import subprocess
r = subprocess.run(["python", "scripts/detect_dark_mode_leaks.py"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(r.stdout)
print(f"Exit: {r.returncode}")
