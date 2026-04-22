# Sentinel Learnings for xpoes123/davidJ

Auto-maintained by Sentinel's memory system. Last updated: 2026-04-22 00:59 UTC

These are patterns learned from completed tasks on this repo.
Claude Code loads this file automatically.

## Warnings (avoid these)

- fetch() without .ok check silently accepts 404/500 responses (confidence: 21)
- Broken asset paths fail silently—check browser console for 404s (confidence: 19)
- innerHTML is XSS-prone; prefer textContent or createElement (confidence: 19)
- Bare catch blocks hide critical errors from debugging (confidence: 15)
- Git credentials in .git/config need immediate rotation (confidence: 13)
- Verify full implementation exists before opening PR (confidence: 11)
- Check git history for exposed tokens even after removal (confidence: 11)
- Animation-heavy designs may cause issues for vestibular users (confidence: 8)
- Copy-pasted code often contains stale references—verify each instance (confidence: 8)
- Generic alt text ('Paper N thumbnail') defeats accessibility purpose (confidence: 8)

## Conventions & Preferences

- Proactive error handling over silent failures (confidence: 18)
- Security-first approach to XSS prevention (confidence: 18)
- Test asset paths work before commit (confidence: 17)
- Explicit HTTP status validation in all fetch chains (confidence: 17)
- Secure git remotes with SSH keys or credential managers (confidence: 16)
- Code cleanup as part of bug scanning (confidence: 15)
- Match spacing patterns (e.g., 48px margin-top for nav clearance) (confidence: 11)
- Accessibility: descriptive alt text and motion preferences respected (confidence: 8)
- Keep font stacks consistent across all pages (confidence: 5)
- Alpha pulsing adds subtle life without being distracting (confidence: 5)

## Learned Patterns

- Check response.ok before parsing fetch responses (confidence: 23)
- Use textContent + createElement instead of innerHTML for dynamic content (confidence: 21)
- Always prepend relative paths for assets (img/, css/, js/) (confidence: 19)
- Scan .git/config for exposed tokens before commits (confidence: 19)
- Always add catch blocks with console.error for fetch calls (confidence: 15)
- Remove dead code during scans (unused functions) (confidence: 15)
- Audit for subtle visual inconsistencies across multiple pages (confidence: 13)
- Match page titles to actual content (research.html ≠ 'Blog') (confidence: 8)
- Add @media (prefers-reduced-motion) blocks for animations (confidence: 8)
- Use descriptive alt text matching actual content, not generic placeholders (confidence: 8)
- Test for content overflow and positioning conflicts (confidence: 6)
- Verify spacing consistency between pages (margin-top, padding standards) (confidence: 6)
- Always use Fisher-Yates for shuffling, never Math.random() - 0.5 (confidence: 6)
- Look for missing font stack entries across pages (confidence: 5)
- Check for unintended cascade effects (e.g., global hover affecting nested elements) (confidence: 5)
