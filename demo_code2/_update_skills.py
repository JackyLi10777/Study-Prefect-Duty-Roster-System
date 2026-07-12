import pathlib

# Update skill-creator
fp = pathlib.Path(r"C:\Users\lichu\.codex\skills\skill-creator\SKILL.md")
c = fp.read_text("utf-8")
addon = """

## Deep-Need Principle

Before creating a skill, ask: what is the user REALLY trying to achieve?
A skill that only addresses the surface request produces faster horses.
A skill that addresses the deeper need builds the automobile.

Example:
- Surface request: Create a skill to fix i18n bugs
- Deeper need: Make the system maintainable and usable by non-English-speaking successors
- Skill should address: auto-detection of i18n gaps, consistency checking, translation workflow

When writing skill instructions, include this prompt:
Before executing, ask what deeper need this task reveals.
"""

idx = c.find("---", 10)
c = c[:idx+3] + addon + c[idx+3:]
fp.write_text(c, "utf-8")
print("skill-creator: updated")

# Update diagnosing-bugs
fp2 = pathlib.Path(r"C:\Users\lichu\.codex\skills\diagnosing-bugs\SKILL.md")
c2 = fp2.read_text("utf-8")
addon2 = """

## Deep-Need Diagnosis

A bug is never just a bug. Every crash reveals:
- A gap in testing (why did not tests catch this?)
- A fragility in architecture (why did one change break three pages?)
- A knowledge gap (why did the developer not anticipate this?)

When diagnosing:
1. Fix the immediate bug (surface issue).
2. Ask: what systemic weakness allowed this bug to exist?
3. Add a guardrail: test, assertion, error handler, or documentation note.
"""
idx2 = c2.find("---", 10)
c2 = c2[:idx2+3] + addon2 + c2[idx2+3:]
fp2.write_text(c2, "utf-8")
print("diagnosing-bugs: updated")

# Update create-plan  
fp3 = pathlib.Path(r"C:\Users\lichu\.codex\skills\create-plan\SKILL.md")
c3 = fp3.read_text("utf-8")
addon3 = """

## Beyond the Surface Plan

A good plan fixes the immediate task. A great plan:
- Identifies the deeper need behind the task
- Includes verification that the deeper need is met
- Leaves the system stronger than before (anti-fragility)

Add one section to every plan: Deeper Need Assessment.
In 1-2 sentences, state what systemic capability this plan builds.
"""
idx3 = c3.find("---", 10)
c3 = c3[:idx3+3] + addon3 + c3[idx3+3:]
fp3.write_text(c3, "utf-8")
print("create-plan: updated")

# Update code-review
fp4 = pathlib.Path(r"C:\Users\lichu\.codex\skills\code-review\SKILL.md")
c4 = fp4.read_text("utf-8")
addon4 = """

## Knowledge Inheritance Review

Beyond code quality, review for knowledge transfer:
- Can a new developer understand WHY decisions were made?
- Are there undocumented assumptions only the original author knows?
- Would this code teach the next person, or confuse them?

Flag any file that scores low on knowledge inheritance --
even if the code is technically correct.
"""
idx4 = c4.find("---", 10)
c4 = c4[:idx4+3] + addon4 + c4[idx4+3:]
fp4.write_text(c4, "utf-8")
print("code-review: updated")

print("\nAll 4 skills updated")
