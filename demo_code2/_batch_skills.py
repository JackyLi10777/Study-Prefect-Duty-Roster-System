import pathlib

skills_dir = pathlib.Path(r"C:\Users\lichu\.codex\skills")

# High-impact skills to give detailed deep-need updates
key_skills = [
    "implement", "check-work", "design", "handoff", "prototype",
    "md-implement", "md-review", "to-issues", "to-prd", "triage",
    "improve-codebase-architecture", "codebase-design", "domain-modeling",
    "review", "shaping",
    # Chinese variants
    "zh-diagnose", "zh-review",
]

deep_note = """

## Deep-Need Awareness (Henry Ford Principle)

> If I asked users what they want, they would say: a faster horse.

Every task request has a deeper need beneath it. Before executing:
1. Fix the surface issue (the faster horse).
2. Ask: what systemic capability is missing? (the automobile).
3. Leave the system stronger than you found it (anti-fragility).
"""

count = 0
for skill_name in key_skills:
    fp = skills_dir / skill_name / "SKILL.md"
    if fp.exists():
        c = fp.read_text("utf-8")
        if "Deep-Need" not in c:
            # Insert after the first --- marker
            idx = c.find("---", 5)
            if idx > 0:
                c = c[:idx+3] + deep_note + c[idx+3:]
                fp.write_text(c, "utf-8")
                count += 1

# Batch: add one-line reminder to ALL remaining skills
one_liner = "\n> Henry Ford: Users ask for faster horses. Dig deeper. What systemic need exists beneath this surface request?\n"
batch_count = 0
for d in sorted(skills_dir.iterdir()):
    if not d.is_dir(): continue
    fp = d / "SKILL.md"
    if not fp.exists(): continue
    if d.name in key_skills + ["skill-creator","create-plan","diagnosing-bugs"]: continue
    c = fp.read_text("utf-8")
    if "Henry Ford" in c or "Deep-Need" in c: continue
    c += one_liner
    fp.write_text(c, "utf-8")
    batch_count += 1

print(f"Key skills updated (detailed): {count}")
print(f"Batch skills updated (one-liner): {batch_count}")
print(f"Total skills touched: {count + batch_count}")
