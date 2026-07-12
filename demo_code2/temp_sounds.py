with open("D:/code_v2/app/components/sounds.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the sounds script with enhanced version
new_script = '''_SOUND_SCRIPT = """
<script>
window._rosterAudio = (function() {
    let ctx = null;
    function getCtx() {
        if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
        if (ctx.state === "suspended") ctx.resume();
        return ctx;
    }
    function tone(freq, duration, type, vol, ramp) {
        try {
            const c = getCtx();
            const o = c.createOscillator();
            const g = c.createGain();
            o.type = type || "sine";
            o.frequency.value = freq;
            g.gain.value = (vol || 0.08);
            const endTime = c.currentTime + duration;
            g.gain.exponentialRampToValueAtTime(0.001, endTime);
            if (ramp) {
                o.frequency.exponentialRampToValueAtTime(freq * ramp, endTime);
            }
            o.connect(g);
            g.connect(c.destination);
            o.start();
            o.stop(endTime);
        } catch(e) { /* silent */ }
    }
    function chime(notes) {
        notes.forEach(function(n, i) {
            setTimeout(function() { tone(n[0], n[1], n[2] || "sine", n[3] || 0.06, n[4]); }, i * (n[5] || 80));
        });
    }
    return {
        // Core actions
        success:  function() { chime([[880,0.15],[1100,0.2,"sine",0.05,1.1]]); },
        warning:  function() { chime([[440,0.12,"triangle",0.05],[440,0.12,"triangle",0.05]]); },
        error:    function() { tone(200, 0.35, "sawtooth", 0.04); },
        click:    function() { tone(660, 0.05, "sine", 0.03); },

        // Enhanced scenarios (v5.5)
        complete: function() {
            chime([[660,0.12],[880,0.15],[1100,0.25,"sine",0.06,1.15]]);
        },
        delete:   function() {
            chime([[440,0.08,"triangle",0.05],[330,0.12,"triangle",0.04]]);
        },
        import:   function() {
            chime([[550,0.1],[660,0.1],[880,0.15],[1100,0.2,"sine",0.06]]);
        },
        export_pdf: function() {
            chime([[880,0.1],[1100,0.12],[1320,0.15,"sine",0.05,1.1]]);
        },
        notification: function() {
            tone(880, 0.08, "sine", 0.04);
        },
    };
})();
</script>
"""'''

content = content.replace('_SOUND_SCRIPT = """\n<script>', new_script.split('_SOUND_SCRIPT = """')[1], 1)

# Fix: replace the entire _SOUND_SCRIPT block
import re
old_script = re.search(r'_SOUND_SCRIPT = """.*?</script>\n"""', content, re.DOTALL)
if old_script:
    content = content[:old_script.start()] + new_script.strip() + content[old_script.end():]

# Add new sound functions
new_functions = '''

def play_complete():
    """Ascending triple-chime for roster generation / PDF export completion."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.complete()")


def play_delete():
    """Descending double-tap for destructive actions (prefect deletion)."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.delete()")


def play_import():
    """Ascending quad-chime for successful CSV import."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.import()")


def play_export_pdf():
    """Ascending triple-chime for PDF/HTML export."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.export_pdf()")


def play_notification():
    """Single soft ping for non-intrusive notifications."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.notification()")'''

# Insert before the last function
content = content.rstrip() + new_functions + "\n"

with open("D:/code_v2/app/components/sounds.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Sounds v5.5 enhanced")
