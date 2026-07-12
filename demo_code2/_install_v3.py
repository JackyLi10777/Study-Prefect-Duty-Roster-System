import pathlib

# v3: Merge user''s regex-negative-lookahead + our CSS override exclusions
script = r'''"""
Dark Mode Color Leak Detector v3
Combines regex-negative-lookahead with CSS override exclusion.
"""

import re
from pathlib import Path
from typing import List, Tuple

DARK_MODE_TOKENS = {
    "background": ["#0F172A", "bg-slate-900"],
    "surface": ["#1E293B", "bg-slate-800"],
    "surface-2": ["#334155", "bg-slate-700"],
    "border": ["#475569", "border-slate-600"],
    "text-primary": ["#F1F5F9", "text-slate-100"],
    "text-secondary": ["#CBD5E1", "text-slate-300"],
}

HIGH_RISK_LIGHT_CLASSES = [
    r"bg-white\b(?!.*dark:)",
    r"bg-slate-50\b(?!.*dark:)",
    r"text-slate-900\b(?!.*dark:)",
    r"border-slate-200\b(?!.*dark:)",
]

SKIP_DIRS = {"__pycache__", "tests", "scripts"}


def detect_dark_mode_compliance(root_dir: str = "app") -> List[Tuple[str, int, str, str]]:
    issues = []
    for py_file in Path(root_dir).rglob("*.py"):
        parts = set(py_file.parts)
        if parts & SKIP_DIRS:
            continue

        content = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            # Skip CSS override rules (these ARE the fixes)
            if "body.dark" in stripped or "!important" in stripped:
                continue
            # Skip design token definitions
            if re.match(r"^[A-Z_]+\s*=\s*", stripped):
                continue
            # Skip CSS variable definitions
            if stripped.startswith("--"):
                continue
            # Skip CSS template blocks
            if "{{" in stripped and "}}" in stripped:
                continue

            for pattern in HIGH_RISK_LIGHT_CLASSES:
                if re.search(pattern, line):
                    issues.append((str(py_file), i, line.strip()[:120],
                                   "Missing dark: variant or centralized override"))
                    break
    return issues


def main():
    print("Dark Mode Design System Compliance Check v3")
    print("=" * 50)
    issues = detect_dark_mode_compliance()

    if not issues:
        print("PASS - Design system dark mode compliant")
        print("Zero high-risk light-mode classes without dark: variants.")
        return 0

    print(f"Found {len(issues)} compliance issues:\n")
    by_file = {}
    for file, line_num, content, reason in issues:
        short = file.replace("app\\", "").replace("\\", "/")
        by_file.setdefault(short, []).append((line_num, content))

    for file, items in sorted(by_file.items()):
        print(f"  {file}:")
        for line_num, content in items:
            print(f"    L{line_num}: {content}")
        print()

    print("Recommendations:")
    for token_name, (hex_color, tailwind_class) in DARK_MODE_TOKENS.items():
        print(f"  {token_name}: {hex_color} / {tailwind_class}")
    return len(issues)


if __name__ == "__main__":
    exit(main())
'''

pathlib.Path(r"D:\code_v2\scripts\detect_dark_mode_leaks.py").write_text(script, "utf-8")
print("v3 detector installed (merged approach)")

import subprocess
r = subprocess.run(["python", "scripts/detect_dark_mode_leaks.py"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(r.stdout)
