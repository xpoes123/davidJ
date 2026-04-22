# Sentinel Learnings for xpoes123/davidJ

Auto-maintained by Sentinel's memory system. Last updated: 2026-04-22 00:58 UTC

These are patterns learned from completed tasks on this repo.
Claude Code loads this file automatically.

## Warnings (avoid these)

- fetch() without .ok check silently accepts 404/500 responses (confidence: 20)
- Broken asset paths fail silently—check browser console for 404s (confidence: 18)
- innerHTML is XSS-prone; prefer textContent or createElement (confidence: 18)
- Bare catch blocks hide critical errors from debugging (confidence: 14)
- Git credentials in .git/config need immediate rotation (confidence: 13)
- Check git history for exposed tokens even after removal (confidence: 11)
- Verify full implementation exists before opening PR (confidence: 10)
- Animation-heavy designs may cause issues for vestibular users (confidence: 7)
- Copy-pasted code often contains stale references—verify each instance (confidence: 7)
- Generic alt text ('Paper N thumbnail') defeats accessibility purpose (confidence: 7)

## Conventions & Preferences

- Proactive error handling over silent failures (confidence: 17)
- Security-first approach to XSS prevention (confidence: 17)
- Test asset paths work before commit (confidence: 16)
- Explicit HTTP status validation in all fetch chains (confidence: 16)
- Secure git remotes with SSH keys or credential managers (confidence: 16)
- Code cleanup as part of bug scanning (confidence: 14)
- Match spacing patterns (e.g., 48px margin-top for nav clearance) (confidence: 7)
- Accessibility: descriptive alt text and motion preferences respected (confidence: 7)
- Alpha pulsing adds subtle life without being distracting (confidence: 5)
- Z-index layering keeps interactive elements accessible (confidence: 5)

## Learned Patterns

- Check response.ok before parsing fetch responses (confidence: 22)
- Use textContent + createElement instead of innerHTML for dynamic content (confidence: 20)
- Scan .git/config for exposed tokens before commits (confidence: 19)
- Always prepend relative paths for assets (img/, css/, js/) (confidence: 18)
- Always add catch blocks with console.error for fetch calls (confidence: 14)
- Remove dead code during scans (unused functions) (confidence: 14)
- Audit for subtle visual inconsistencies across multiple pages (confidence: 12)
- Match page titles to actual content (research.html ≠ 'Blog') (confidence: 7)
- Add @media (prefers-reduced-motion) blocks for animations (confidence: 7)
- Use descriptive alt text matching actual content, not generic placeholders (confidence: 7)
- Always use Fisher-Yates for shuffling, never Math.random() - 0.5 (confidence: 6)
- Canvas-based effects perform better than DOM-heavy animations (confidence: 5)
- Look for missing font stack entries across pages (confidence: 4)
- Verify spacing consistency between pages (margin-top, padding standards) (confidence: 4)
- Check for unintended cascade effects (e.g., global hover affecting nested elements) (confidence: 4)
