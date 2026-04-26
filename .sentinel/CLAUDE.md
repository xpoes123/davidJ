# Sentinel Learnings for xpoes123/davidJ

Auto-maintained by Sentinel's memory system. Last updated: 2026-04-26 16:46 UTC

These are patterns learned from completed tasks on this repo.
Claude Code loads this file automatically.

## Warnings (avoid these)

- fetch() without .ok check silently accepts 404/500 responses (confidence: 34)
- Broken asset paths fail silently—check browser console for 404s (confidence: 31)
- innerHTML is XSS-prone; prefer textContent or createElement (confidence: 30)
- Bare catch blocks hide critical errors from debugging (confidence: 27)
- Copy-pasted code often contains stale references—verify each instance (confidence: 18)
- Verify full implementation exists before opening PR (confidence: 17)
- Git credentials in .git/config need immediate rotation (confidence: 13)
- Absolute-positioned elements like 'Home' links need margin buffer below (confidence: 11)
- Mismatched line-height/font-size kills readability—sync similar components (confidence: 11)
- Check git history for exposed tokens even after removal (confidence: 11)

## Conventions & Preferences

- Test asset paths work before commit (confidence: 33)
- Security-first approach to XSS prevention (confidence: 30)
- Explicit HTTP status validation in all fetch chains (confidence: 25)
- Proactive error handling over silent failures (confidence: 20)
- Match spacing patterns (e.g., 48px margin-top for nav clearance) (confidence: 18)
- Code cleanup as part of bug scanning (confidence: 17)
- Throw descriptive errors with HTTP status codes (confidence: 16)
- Secure git remotes with SSH keys or credential managers (confidence: 16)
- Automated scanning followed by manual review and PR (confidence: 13)
- Document specific changes in issue tables (confidence: 11)

## Learned Patterns

- Check response.ok before parsing fetch responses (confidence: 33)
- Use textContent + createElement instead of innerHTML for dynamic content (confidence: 30)
- Always prepend relative paths for assets (img/, css/, js/) (confidence: 30)
- Scan .git/config for exposed tokens before commits (confidence: 26)
- Audit for subtle visual inconsistencies across multiple pages (confidence: 25)
- Always add catch blocks with console.error for fetch calls (confidence: 18)
- Use descriptive alt text matching actual content, not generic placeholders (confidence: 17)
- Remove dead code during scans (unused functions) (confidence: 17)
- Test for content overflow and positioning conflicts (confidence: 13)
- Check for existing implementations before building from scratch (confidence: 10)
- Match page titles to actual content (research.html ≠ 'Blog') (confidence: 10)
- Add @media (prefers-reduced-motion) blocks for animations (confidence: 10)
- Exit code 1 on any breakage forces PR blocking without config (confidence: 8)
- GitHub PAT workflow scope required for .github/workflows/ commits (confidence: 8)
- Link validation via filesystem walk + regex extraction on HTML attrs (confidence: 8)
