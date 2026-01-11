# Deploy to Production

Commit all changes and push to GitHub (triggers Vercel deploy).

## Instructions

1. Run `git status` to see all changes
2. Run `git diff --stat` to summarize what changed
3. Stage all changes with `git add -A`
4. Generate a concise commit message based on the changes:
   - Use conventional commit format (feat:, fix:, docs:, refactor:, etc.)
   - Summarize the main changes in 1-2 lines
   - Add "Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>" at the end
5. Commit with the generated message
6. Push to origin/main
7. Report success with the commit hash and a brief summary

## Important

- Do NOT commit files containing secrets (.mcp.json, mcp_config, .env, etc.)
- If push fails due to secrets, unstage those files and add them to .gitignore
- Update the version label in api/static/index.html if significant changes were made
