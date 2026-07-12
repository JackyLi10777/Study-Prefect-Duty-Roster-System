import pathlib

# ===== 1. GROK_PROMPTS.md: Add ODI section after JTBD =====
p = pathlib.Path(r"D:\code_v2\GROK_PROMPTS.md")
c = p.read_text("utf-8")

odi_section = """

### The ODI Lens: Which Outcomes Matter Most?

While JTBD tells us WHAT job is being hired, Outcome-Driven Innovation (ODI) tells us
WHICH specific outcomes are most worth pursuing — quantitatively.

**The Opportunity Score:**
```
Opportunity Score = Importance + (Importance - Satisfaction)
```

Where Importance and Satisfaction are rated 1-10 by the user for each Desired Outcome.

| Score Range | Meaning | Action |
|------------|---------|--------|
| High Importance + Low Satisfaction | Underserved outcome | Highest priority for innovation |
| High Importance + High Satisfaction | Served outcome | Maintain, do not over-invest |
| Low Importance | Not worth pursuing | Deprioritize |

**Applying ODI to Codex tasks:**

When a user requests a feature or fix, reframe it as a Desired Outcome:
- Not: "I want dark mode on the sidebar"
- But: "I want to reduce eye strain when using the system at night" (Importance: 9, Satisfaction: 2)

This reveals the Opportunity Score (9 + 7 = 16) — a high-value innovation target.

Then ask: does the requested solution (dark mode sidebar) maximize progress toward this outcome,
or is there a better way to achieve it?
"""

idx = c.find("### The JTBD Lens")
if idx > 0:
    # Find end of JTBD section
    next_section = c.find("---", idx)
    c = c[:next_section] + "\n" + odi_section + "\n" + c[next_section:]

p.write_text(c, "utf-8")
print("1. GROK_PROMPTS.md: ODI section with Opportunity Score added")

# ===== 2. decision-mapping: Add Opportunity Score template =====
fp = pathlib.Path(r"C:\Users\lichu\.codex\skills\decision-mapping\SKILL.md")
if fp.exists():
    c2 = fp.read_text("utf-8")
    odi_dm = """

## Opportunity Score Assessment

When evaluating competing options, quantify the opportunity:

For each desired outcome the user cares about:
1. Rate Importance (1-10): How critical is this outcome to the user?
2. Rate Satisfaction (1-10): How well do current solutions meet this outcome?
3. Calculate: Opportunity = Importance + (Importance - Satisfaction)
4. Target outcomes with the highest Opportunity Score.

This transforms subjective preference into data-driven prioritization.
"""
    idx2 = c2.find("##", 20)
    if idx2 > 0:
        c2 = c2[:idx2] + odi_dm + "\n" + c2[idx2:]
    fp.write_text(c2, "utf-8")
    print("2. decision-mapping: Opportunity Score template added")

# ===== 3. skill-creator: Add Desired Outcome template =====
fp3 = pathlib.Path(r"C:\Users\lichu\.codex\skills\skill-creator\SKILL.md")
c3 = fp3.read_text("utf-8")

odi_skill = """

## Desired Outcome Assessment (ODI)

Before designing a skill, define the Desired Outcomes it should produce.
Desired Outcomes must be:
- Measurable (can be rated on Importance and Satisfaction)
- Customer-centric (from the user's perspective, not the developer's)
- Solution-independent (describe the result, not the feature)

Example:
- Not: "The skill should generate code" (solution-dependent)
- But: "The user should spend less time writing boilerplate" (outcome-focused)
"""
idx3 = c3.find("## JTBD Analysis Template")
if idx3 > 0:
    c3 = c3[:idx3] + odi_skill + "\n" + c3[idx3:]
fp3.write_text(c3, "utf-8")
print("3. skill-creator: Desired Outcome Assessment added")

print("\nODI framework integrated")
