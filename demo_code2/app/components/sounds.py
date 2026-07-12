"""
Subtle audio feedback for key interactions. v5.5 Fluid Edition.
Uses Web Audio API — no external files needed.
Restrained, professional tones suitable for a school administration tool.
Enhanced with multi-note chimes for richer feedback.
"""
from nicegui import ui


_SOUND_SCRIPT = """
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
        success:  function() { chime([[880,0.15],[1100,0.2,"sine",0.05,1.1]]); },
        warning:  function() { chime([[440,0.12,"triangle",0.05],[440,0.12,"triangle",0.05]]); },
        error:    function() { tone(200, 0.35, "sawtooth", 0.04); },
        click:    function() { tone(660, 0.05, "sine", 0.03); },
        complete: function() { chime([[660,0.12],[880,0.15],[1100,0.25,"sine",0.06,1.15]]); },
        delete:   function() { chime([[440,0.08,"triangle",0.05],[330,0.12,"triangle",0.04]]); },
        import:   function() { chime([[550,0.1],[660,0.1],[880,0.15],[1100,0.2,"sine",0.06]]); },
        export_pdf: function() { chime([[880,0.1],[1100,0.12],[1320,0.15,"sine",0.05,1.1]]); },
        notification: function() { tone(880, 0.08, "sine", 0.04); },
    };
})();
</script>
"""

_injected = False


def inject_sound_api():
    """Inject the Web Audio sound API into the page. Call once in main.py."""
    global _injected
    if not _injected:
        ui.add_head_html(_SOUND_SCRIPT, shared=True)
        _injected = True


def play_success():
    """Gentle ascending double-chime for successful actions."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.success()")


def play_warning():
    """Soft double-tap for attention-needed situations."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.warning()")


def play_error():
    """Low subtle buzz for error conditions."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.error()")


def play_click():
    """Very short click for button presses."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.click()")


def play_complete():
    """Ascending triple-chime for roster generation / PDF export completion."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.complete()")


def play_delete():
    """Descending double-tap for destructive actions."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.delete()")


def play_import():
    """Ascending quad-chime for successful CSV import."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.import()")


def play_export_pdf():
    """Ascending triple-chime for PDF/HTML export."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.export_pdf()")


def play_notification():
    """Single soft ping for non-intrusive notifications."""
    ui.run_javascript("window._rosterAudio && _rosterAudio.notification()")
