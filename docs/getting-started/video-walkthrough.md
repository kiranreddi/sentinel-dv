# Video Walkthrough

This 45-second walkthrough shows the real documentation surface, the supported
agent setup paths, and the three verified Sentinel DV workflows. It has no
narration or audio.

<div class="sdv-video">
  <video
    controls
    playsinline
    preload="metadata"
    poster="../../assets/videos/sentinel-dv-quickstart-poster.jpg"
    aria-label="Sentinel DV setup and workflow walkthrough"
  >
    <source src="../../assets/videos/sentinel-dv-quickstart.mp4" type="video/mp4">
    Your browser does not support embedded MP4 video.
  </video>
</div>

## Scene index

| Time | Scene | What is shown |
| --- | --- | --- |
| 0:00 | Product boundary | 28 read-only tools, three workflow skills, and no simulator control |
| 0:07 | Agent setup | MCP and project-skill setup for Codex, Claude Code, and GitHub Copilot |
| 0:16 | Regression triage | A real health response with unavailable cohort data excluded from scoring |
| 0:26 | Debug and closure | Bounded waveform evidence and an engineer-reviewed coverage candidate |
| 0:36 | Verification | Deterministic checks for all MCP tools and all three skill workflows |

## Reproduce the checks

From a development checkout:

```bash
.venv/bin/python scripts/verify_all_mcp_tools.py
.venv/bin/python scripts/verify_skill_workflows.py
.venv/bin/python scripts/sync_agent_skills.py --check
```

The video is a product walkthrough, not a sign-off claim. Sentinel DV reads
exported artifacts and returns bounded evidence. It does not run simulations,
modify verification sources, or certify coverage closure.

[Connect an agent](agent-setup.md){ .md-button .md-button--primary }
[Inspect real tool output](../tools/mcp-tool-gallery.md){ .md-button }
