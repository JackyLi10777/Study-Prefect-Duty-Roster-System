import pathlib

# ===== 1. GROK_PROMPTS.md: Add JTBD section after Section 0 =====
p = pathlib.Path(r"D:\code_v2\GROK_PROMPTS.md")
c = p.read_text("utf-8")

jtbd_section = """

### The JTBD Lens: What Job Is Being Hired?

Every surface request is a user "hiring" a solution to make progress in their life.
The real question is: what job are they hiring this solution to do?

**Three layers of every job:**

| Layer | Question | Example: "Add logging" |
|-------|----------|----------------------|
| Functional | What task needs doing? | "Write log entries to a file" |
| Emotional | How should the user feel? | "I want to feel confident I can find errors" |
| Social | How should others perceive? | "I want successors to see I built a maintainable system" |

**The 8-step Job Map:**
1. Define the job | 2. Locate solutions | 3. Prepare | 4. Confirm
5. Execute | 6. Monitor | 7. Modify | 8. Conclude

**Applying JTBD to Codex tasks:**
Before executing, ask:
- What PROGRESS is the user trying to make? (Not: what feature do they want?)
- What is the context? When and why does this need arise?
- Would a fundamentally different solution help them make progress faster, better, or more enjoyably?
- Am I optimizing a horse, or could I build an automobile?
"""

# Insert after Section 0
idx = c.find("### How to Apply")
if idx > 0:
    # Find the end of the Apply section
    end = c.find("---", idx)
    c = c[:end] + "\n" + jtbd_section + "\n" + c[end:]

p.write_text(c, "utf-8")
print("1. GROK_PROMPTS.md: JTBD section added")

# ===== 2. skill-creator: Add JTBD template =====
fp = pathlib.Path(r"C:\Users\lichu\.codex\skills\skill-creator\SKILL.md")
c2 = fp.read_text("utf-8")

jtbd_skill = """

## JTBD Analysis Template (Use Before Creating Any Skill)

Before writing the skill, complete this 3-line analysis:

1. **Progress**: What progress is the user trying to make?
   (Not: what skill do they want? What outcome are they hiring this skill to produce?)

2. **Context**: When and why does this need arise?
   (What situation triggers the need for this skill? What emotional/social factors matter?)

3. **Better Way**: Is there a fundamentally different approach that would help them
   make progress faster, better, or more enjoyably than what they are asking for?
   (If yes, propose it alongside the requested approach.)
"""

idx2 = c2.find("## Deep-Need Principle")
if idx2 > 0:
    c2 = c2[:idx2] + jtbd_skill + "\n" + c2[idx2:]
fp.write_text(c2, "utf-8")
print("2. skill-creator: JTBD Analysis Template added")

# ===== 3. create-plan: Add JTBD goal clarification =====
fp3 = pathlib.Path(r"C:\Users\lichu\.codex\skills\create-plan\SKILL.md")
c3 = fp3.read_text("utf-8")

jtbd_plan = """

## JTBD Goal Check (Before Planning)

Ask these questions before writing the plan:
1. What progress is the user hiring this plan to produce?
2. What functional, emotional, or social job does this plan serve?
3. Would the user feel confident, relieved, or proud after this plan executes?
4. Is this plan optimizing a horse (incremental fix) or building an automobile (systemic capability)?
"""

idx3 = c3.find("## Beyond the Surface Plan")
if idx3 > 0:
    c3 = c3[:idx3] + jtbd_plan + "\n" + c3[idx3:]
fp3.write_text(c3, "utf-8")
print("3. create-plan: JTBD Goal Check added")

print("\nJTBD framework integrated")
