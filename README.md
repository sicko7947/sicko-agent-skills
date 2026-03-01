# Agent Skills

A collection of reusable skills for AI coding agents (Claude Code, Codex, etc.).

## Skills

| Skill | Description |
|-------|-------------|
| [pr-manager](./pr-manager/) | Automates PR creation, review monitoring, feedback implementation, and reviewer coordination |
| [gemini-file-search](./gemini-file-search/) | Complete reference for Google Gemini File Search API — managed RAG with stores, uploads, metadata filtering, and known issues |

## Installation

### Claude Code

Symlink skills into `~/.claude/skills/`:

```bash
ln -s /path/to/agent-skills/pr-manager ~/.claude/skills/pr-manager
ln -s /path/to/agent-skills/gemini-file-search ~/.claude/skills/gemini-file-search
```

### Other Agents

Copy or symlink skill directories into your agent's skill directory.

## License

MIT
