# Sentinel Learnings for xpoes123/davidJ

Auto-maintained by Sentinel's memory system. Last updated: 2026-04-22 00:51 UTC

These are patterns learned from completed tasks on this repo.
Claude Code loads this file automatically.

## Warnings (avoid these)

- fetch() without .ok check silently accepts 404/500 responses (confidence: 17)
- innerHTML is XSS-prone; prefer textContent or createElement (confidence: 16)
- Broken asset paths fail silently—check browser console for 404s (confidence: 15)
- Git credentials in .git/config need immediate rotation (confidence: 13)
- Bare catch blocks hide critical errors from debugging (confidence: 12)
- Check git history for exposed tokens even after removal (confidence: 11)
- Verify full implementation exists before opening PR (confidence: 8)
- Token exposure can grant full repo write access to attackers (confidence: 7)
- HTTPS URLs with embedded credentials should never be committed (confidence: 6)
- Never use .sort(() => Math.random() - 0.5) for shuffling (confidence: 6)

## Conventions & Preferences

- Secure git remotes with SSH keys or credential managers (confidence: 16)
- Proactive error handling over silent failures (confidence: 15)
- Security-first approach to XSS prevention (confidence: 15)
- Test asset paths work before commit (confidence: 14)
- Explicit HTTP status validation in all fetch chains (confidence: 14)
- Code cleanup as part of bug scanning (confidence: 11)
- Accessibility: descriptive alt text and motion preferences respected (confidence: 5)
- Match spacing patterns (e.g., 48px margin-top for nav clearance) (confidence: 5)
- Alpha pulsing adds subtle life without being distracting (confidence: 5)
- Z-index layering keeps interactive elements accessible (confidence: 5)

## Learned Patterns

- Check response.ok before parsing fetch responses (confidence: 19)
- Scan .git/config for exposed tokens before commits (confidence: 19)
- Use textContent + createElement instead of innerHTML for dynamic content (confidence: 18)
- Always prepend relative paths for assets (img/, css/, js/) (confidence: 15)
- Always add catch blocks with console.error for fetch calls (confidence: 12)
- Remove dead code during scans (unused functions) (confidence: 12)
- Audit for subtle visual inconsistencies across multiple pages (confidence: 9)
- Always use Fisher-Yates for shuffling, never Math.random() - 0.5 (confidence: 6)
- Add @media (prefers-reduced-motion) blocks for animations (confidence: 5)
- Use descriptive alt text matching actual content, not generic placeholders (confidence: 5)
- Canvas-based effects perform better than DOM-heavy animations (confidence: 5)
- Match page titles to actual content (research.html ≠ 'Blog') (confidence: 5)
- Check for existing implementations before building from scratch (confidence: 4)
- Particle systems work well for CS/quant portfolio aesthetics (confidence: 4)
- Mouse interaction creates memorable micro-interactions (confidence: 4)
