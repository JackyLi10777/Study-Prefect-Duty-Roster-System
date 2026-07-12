import pathlib
script = '''"""
Dark Mode Color Leak Detector
Automatically finds potential light mode color leaks in dark mode.
Scans all .py files in the app/ directory for Tailwind light-mode classes
that lack corresponding dark: variants.
"""

import re
from pathlib import Path
from typing import List, Tuple

LIGHT_MODE_PATTERNS = [
    r"bg-white\\b",
    r"bg-slate-50\\b",
    r"bg-gray-50\\b",
    r"text-slate-900\\b",
    r"text-black\\b",
    r"border-slate-200\\b",
    r"border-gray-300\\b",
    r"shadow-sm\\b",
]

def find_leaks(root_dir: str = "app") -> List[Tuple[str, int, str]]:
    leaks = []
    root_path = Path(root_dir)

    for py_file in root_path.rglob("*.py"):
        if "test" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                if line.strip().startswith("#"):
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
    print("Scanning for Dark Mode Color Leaks...\\n")
    leaks = find_leaks()

    if not leaks:
        print("No obvious light mode color leaks detected!")
        return 0

    print(f"Found {len(leaks)} potential light mode color leaks:\\n")
    for file, line_num, content in leaks:
        print(f"  {file}:{line_num}")
        print(f"    {content}\\n")

    print("Recommendations:")
    print("  1. Add dark: variants to these locations")
    print("  2. Or add centralized override rules in theme/css.py")
    print("  3. Re-run this script to confirm fixes")
    return 1


if __name__ == "__main__":
    exit(main())
'''
pathlib.Path(r"D:\code_v2\scripts\detect_dark_mode_leaks.py").write_text(script, "utf-8")
print("Script created")
