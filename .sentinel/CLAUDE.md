# Sentinel Learnings for xpoes123/davidJ

Auto-maintained by Sentinel's memory system. Last updated: 2026-04-19 06:45 UTC

These are patterns learned from completed tasks on this repo.
Claude Code loads this file automatically.

## Warnings (avoid these)

- Never use .sort(() => Math.random() - 0.5) for shuffling
- innerHTML is XSS-prone; prefer textContent or createElement
- fetch() without .ok check silently accepts 404/500 responses
- Bare catch blocks hide critical errors from debugging
- Git credentials in .git/config need immediate rotation
- Check git history for exposed tokens even after removal

## Conventions & Preferences

- Proactive error handling over silent failures
- Security-first approach to XSS prevention
- Explicit HTTP status validation in all fetch chains
- Code cleanup as part of bug scanning

## Learned Patterns

- Always use Fisher-Yates for shuffling, never Math.random() - 0.5
- Use textContent + createElement instead of innerHTML for dynamic content
- Check response.ok before parsing fetch responses
- Always add catch blocks with console.error for fetch calls
- Remove dead code during scans (unused functions)
- Scan .git/config for exposed tokens before commits
