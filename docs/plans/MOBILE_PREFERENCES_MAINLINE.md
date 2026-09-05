# Mainline integration D1: first-use mobile preferences

Base: freshly fetched protected main `cb12fd0a2f1d2adca1af7cffacbb150f0c3bd801`
after C (#130). This is an independent, bounded D checkpoint, not adoption of the
entire frozen `856d06c` branch. Original and frozen worktrees remain unchanged.

## Scope

- All existing sidebar navigation and portal links precede mobile preferences.
- Initial page/drawer rendering creates only a closed disclosure and empty
  content host. Opening the drawer does not build preference controls.
- First explicit preference expansion reads current locale, sound, appearance
  and page principal mode, then mounts the existing controls once. Collapsing
  retains the controls and their registrations; no per-open renderer or listener.
- A persistent header theme control is the browser appearance source when a
  late drawer control carries older server state. Existing runtime sync updates
  its preference, resolved icon, action label and state without animation.
- Collapsing while focus is inside the content returns focus to the disclosure
  header. Existing drawer Escape/focus handling, routes, identity and logout
  paths are unchanged.

No audio defaults/runtime, GSAP, Worker, database, export/GET/PNG, other pages or
settings-module changes belong to D1. No deployment or business activation.

## Evidence and remaining acceptance

Four red tests reproduced eager mounting for Admin/Guest and stale late theme
overrides in both directions. The repair passes 46 focused tests across mobile
preferences, quick settings, theme preference and mobile layout. Lifecycle tests
call the real callbacks 20 times and prove one control set and registration pair;
Node executes the existing theme runtime for the late-insertion cases. These are
focused tests, not real-browser or controlled-performance acceptance.

Real browser first-use absence, navigation order, 20-cycle identity/growth,
focus/collapse/Escape, current sound/theme/language, Guest logout, narrow reflow
and full verification remain required before merge. Heavy browser/full work is
serialized with the other local integration task; no threshold is relaxed.

Subsequent D batches must address genuine first-use access technical controls,
support advanced/history and showcase content, not merely collapsed eager
expansions. Other remaining mobile pages and quiet audio/idle animation are
separate scoped follow-ups. D1 does not claim those tasks complete.
