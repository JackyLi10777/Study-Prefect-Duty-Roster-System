"""Local, accessibility-aware motion runtime injected on every NiceGUI page."""

MOTION_HEAD_HTML = """
<script data-sy-runtime="motion-loader">
(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const script = document.createElement('script');
  script.src = '/assets/vendor/gsap-3.13.0.min.js';
  script.async = false;
  document.head.append(script);
})();
</script>
<script defer src="/assets/motion/sing-yin-icon-story-state.js"></script>
<script defer src="/assets/motion/sing-yin-motion.js"></script>
"""
