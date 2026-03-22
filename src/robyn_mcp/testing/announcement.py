from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AnnouncementBundle:
    out_dir: Path
    markdown_path: Path
    social_card_path: Path
    summary_path: Path

    def as_dict(self) -> dict[str, str]:
        return {
            'outDir': str(self.out_dir),
            'markdownPath': str(self.markdown_path),
            'socialCardPath': str(self.social_card_path),
            'summaryPath': str(self.summary_path),
        }


def build_announcement_bundle(project_root: str | Path, out_dir: str | Path) -> AnnouncementBundle:
    root = Path(project_root)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    version = '1.0.0'
    markdown = out / 'announcement.md'
    markdown.write_text(
        f"# robyn_mcp {version}\n\n"
        "robyn_mcp turns Robyn routes into MCP tools, resources, and prompts with auth-aware exposure, "
        "schema generation, transport support, validation tooling, and release assets.\n\n"
        "## Launch highlights\n"
        "- Robyn-native MCP adapter with HTTP transport\n"
        "- auth, policy, rate-limiting, and validation hooks\n"
        "- tools, resources, and prompts support\n"
        "- docs website, CLI, editor integrations, and launch bundle\n"
    )

    social = out / 'social_card.svg'
    social.write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='630' viewBox='0 0 1200 630'>"
        "<rect width='1200' height='630' fill='#0b1020'/>"
        "<text x='80' y='180' fill='#e2e8f0' font-size='58' font-family='Arial'>robyn_mcp 1.0.0</text>"
        "<text x='80' y='260' fill='#93c5fd' font-size='34' font-family='Arial'>Robyn routes to MCP tools, resources, and prompts</text>"
        "<text x='80' y='330' fill='#cbd5e1' font-size='28' font-family='Arial'>Launch-ready docs, validation CLI, website export, and editor integrations</text>"
        "</svg>"
    )

    summary = out / 'summary.json'
    summary.write_text(json.dumps({
        'version': version,
        'releaseNotes': str(root / 'docs' / 'release_notes_v0_17_0.md'),
        'publicLaunchDoc': str(root / 'docs' / 'public_launch.md'),
        'marketplaceDoc': str(root / 'docs' / 'marketplace_submission.md'),
    }, indent=2))

    return AnnouncementBundle(out, markdown, social, summary)
