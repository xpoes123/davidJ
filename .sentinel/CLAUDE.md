# Sentinel Learnings for xpoes123/davidJ

Auto-maintained by Sentinel's memory system. Last updated: 2026-04-24 12:32 UTC

These are patterns learned from completed tasks on this repo.
Claude Code loads this file automatically.

## Warnings (avoid these)

- fetch() without .ok check silently accepts 404/500 responses (confidence: 32)
- Broken asset paths fail silently—check browser console for 404s (confidence: 29)
- innerHTML is XSS-prone; prefer textContent or createElement (confidence: 28)
- Bare catch blocks hide critical errors from debugging (confidence: 22)
- Copy-pasted code often contains stale references—verify each instance (confidence: 16)
- Verify full implementation exists before opening PR (confidence: 15)
- Git credentials in .git/config need immediate rotation (confidence: 13)
- Mismatched line-height/font-size kills readability—sync similar components (confidence: 11)
- Check git history for exposed tokens even after removal (confidence: 11)
- Animation-heavy designs may cause issues for vestibular users (confidence: 10)

## Conventions & Preferences

- Test asset paths work before commit (confidence: 31)
- Security-first approach to XSS prevention (confidence: 27)
- Explicit HTTP status validation in all fetch chains (confidence: 23)
- Proactive error handling over silent failures (confidence: 20)
- Code cleanup as part of bug scanning (confidence: 17)
- Match spacing patterns (e.g., 48px margin-top for nav clearance) (confidence: 16)
- Secure git remotes with SSH keys or credential managers (confidence: 16)
- Throw descriptive errors with HTTP status codes (confidence: 13)
- Automated scanning followed by manual review and PR (confidence: 11)
- Accessibility: descriptive alt text and motion preferences respected (confidence: 10)

## Learned Patterns

- Check response.ok before parsing fetch responses (confidence: 31)
- Use textContent + createElement instead of innerHTML for dynamic content (confidence: 28)
- Always prepend relative paths for assets (img/, css/, js/) (confidence: 28)
- Scan .git/config for exposed tokens before commits (confidence: 24)
- Audit for subtle visual inconsistencies across multiple pages (confidence: 23)
- Always add catch blocks with console.error for fetch calls (confidence: 17)
- Remove dead code during scans (unused functions) (confidence: 17)
- Use descriptive alt text matching actual content, not generic placeholders (confidence: 15)
- Test for content overflow and positioning conflicts (confidence: 11)
- Match page titles to actual content (research.html ≠ 'Blog') (confidence: 10)
- Add @media (prefers-reduced-motion) blocks for animations (confidence: 10)
- Check for existing implementations before building from scratch (confidence: 8)
- Verify spacing consistency between pages (margin-top, padding standards) (confidence: 8)
- Look for missing font stack entries across pages (confidence: 7)
- Check for unintended cascade effects (e.g., global hover affecting nested elements) (confidence: 7)
