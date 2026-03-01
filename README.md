# Agent Skills

A collection of reusable skills for AI coding agents.

## Skills

| Skill | Description |
|-------|-------------|
| [pr-manager](./skills/pr-manager/) | Automates PR creation, review monitoring, feedback implementation, and reviewer coordination |
| [gemini-file-search](./skills/gemini-file-search/) | Complete reference for Google Gemini File Search API — managed RAG with stores, uploads, metadata filtering, and known issues |

## Installation

### Claude Code (Plugin)

```bash
/plugin install https://github.com/sicko7947/agent-skills
```

Skills are automatically available as `/agent-skills:pr-manager` and `/agent-skills:gemini-file-search`.

### Manual

Symlink individual skills into `~/.claude/skills/`:

```bash
git clone https://github.com/sicko7947/agent-skills.git ~/.agents/agent-skills
ln -s ~/.agents/agent-skills/skills/pr-manager ~/.claude/skills/pr-manager
ln -s ~/.agents/agent-skills/skills/gemini-file-search ~/.claude/skills/gemini-file-search
```

## License

MIT
