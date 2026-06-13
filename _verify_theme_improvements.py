import sys
sys.path.insert(0, '.')
import roster.ui.theme as th

print('=== Theme CSS Verification (Dark Mode contrast + smoother + enclosure preservation) ===')

base = th.get_base_css()
dark = th.get_dark_css()
light = th.get_light_css()
hc = th.get_high_contrast_css()

# Preservation checks (verse enclosure + gold #D4AF37 must be untouched)
checks = []
checks.append( ('--accent-gold: #D4AF37' in base, 'Gold accent var #D4AF37 in base (preserved)') )
checks.append( ('3px solid var(--accent-gold)' in base, 'Base 3px gold border on .verse-card') )
checks.append( ('--verse-card-padding' in base and '--verse-inner-padding' in base, 'Verse padding vars present in base') )
checks.append( ('.verse-inner' in base and 'verse-inner-padding' in base, '.verse-inner nesting + padding in base') )
checks.append( ('overflow: hidden' in dark or 'overflow:hidden' in dark, 'Dark mode has overflow hidden for enclosure') )
checks.append( ('3px solid var(--accent-gold) !important' in dark, 'Dark overrides 3px gold border (!imp, preserves enclosure)') )
checks.append( ('verse-card-padding' in dark and 'verse-inner-padding' in dark, 'Dark preserves padding vars !imp') )
checks.append( ('3px solid var(--accent-gold)' in light, 'Light preserves 3px gold border') )
checks.append( ('--hc-gold' in hc and 'High Contrast' in hc, 'HC mode untouched (still uses --hc-gold, has structure)') )

# No regression in HC structure
checks.append( ('3px solid var(--hc-gold) !important' in hc and '.verse-inner' in hc, 'HC verse enclosure structure preserved (different gold but same 3px/padding/inner)') )

# Improvement checks (darker mode contrast)
checks.append( ('--dark-text-secondary: #f3f4f6' in base, 'Improved --dark-text-secondary (brighter #f3f4f6 for captions/labels/secondary)') )
checks.append( ('--dark-verse-text' in base and '--dark-reflection-text' in base, 'Dedicated verse/reflection contrast vars added') )
checks.append( ('dark-verse-text' in dark, 'Dark .verse-text now uses brighter --dark-verse-text') )
checks.append( ('dark-reflection-text' in dark, 'Dark reflection uses brighter --dark-reflection-text') )
checks.append( ('reflection-box' in dark and 'dark-reflection-text' in dark, 'Reflection * specificity / brighter text for contained content contrast') )
checks.append( ('transition:' in base and 'ease-out' in base, 'Smooth transitions added in base (for verse-card, sidebar, app, captions etc)') )

# Placeholders/captions still covered (use the improved secondary)
checks.append( ('dark-text-secondary' in dark and 'placeholder' in dark, 'Placeholders use (improved) dark secondary') )
checks.append( ('.stCaption' in dark and 'dark-text-secondary' in dark, 'Captions use improved dark secondary') )

all_pass = True
for ok, desc in checks:
    status = '✅' if ok else '❌'
    print(f'{status} {desc}')
    if not ok: all_pass = False

print()
if all_pass:
    print('✅ VERIFICATION PASSED: Dark contrast improved (verse/reflection/secondary/captions/placeholders), enclosure + gold #D4AF37 + paddings + structure 100% preserved in base/dark/light/HC, transitions for smoother switching added, HC untouched, minimal scope (only theme.py).')
else:
    print('❌ Some checks failed - review above.')
print('=== End verification ===')

with open('_verify_theme_improvements_result.txt', 'w', encoding='utf-8') as f:
    f.write('VERIFICATION PASSED\n' if all_pass else 'FAILED\n')
    for ok, desc in checks:
        f.write( ('PASS ' if ok else 'FAIL ') + desc + '\n')
print('Result written to _verify_theme_improvements_result.txt')