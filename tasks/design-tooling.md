# Design tools and Stitch handoff

Recorded 2026-09-14. User authorized exporting the existing wireframe for continued design in Google Stitch and installing Stitch skills plus Impeccable for later frontend work. This does not authorize application scaffolding or implementation.

## Installed skills

Used Codex's skill-installer helper to copy the requested upstream skill directories, pinned to the inspected repository revisions. No existing skills were overwritten.

| Source | Revision | Installed location | Result |
| --- | --- | --- | --- |
| [Google Labs Stitch skills](https://github.com/google-labs-code/stitch-skills) | 0337446dadde6f8c94210444e2aa9d546126480f | C:/Users/Sebas/.codex/skills | 16 skills |
| [Impeccable](https://github.com/pbakaus/impeccable) | 2149fcce39a90bb409df5f16515f316a76dc6199 | C:/Users/Sebas/.agents/skills/impeccable | Skill, references, agents, and launchers |

Stitch directories: code-to-design, extract-design-md, extract-static-html, generate-design, manage-design-system, upload-to-stitch, react-components, react-native, react-vite-dashboard, remotion, shadcn-ui, design-md, enhance-prompt, site-md, stitch-loop, taste-design. Installing the collection is preparation; it is not a commitment to use its framework-specific build skills.

Impeccable's SKILL.md metadata reports version 4.3.1; its scripts/VERSION reports launcher engine 0.1.5. The upstream launchers can retrieve their pinned engine on first use. This was a skill installation: no Impeccable project hooks, live browser extension, PRODUCT.md initialization, or automatic design audit was activated. Existing planning and the user's palette remain authoritative.

The skills are available for discovery on the next turn. If a client still shows an older skill list, restart it. No Stitch MCP tool is connected in this session; the skill repository documents a separate [MCP setup](https://stitch.withgoogle.com/docs/mcp/setup/) for direct agent access. The manual import handoff works independently of that connection.

## Export

Original handoff design document: [.stitch/DESIGN.md](../.stitch/DESIGN.md). Export directory: [design/stitch-handoff](../design/stitch-handoff/README.md). The earlier ZIP remains in the parent workspace archive; its extracted files are versioned here. For the current reviewed direction, see [design references](../design/README.md).

The handoff contains the design document, continuation prompt, screen map, portable walkthrough, 18 desktop and 18 mobile screenshots, corresponding static HTML snapshots, a visual index, source/inventory hashes, and Lucide's license notice. It uses only sample data from the existing walkthrough. User-attached screenshots of the installer/Stitch UI are not redistributed in the package.

The original in-conversation fragment was preserved. The visualize export renderer generated the standalone document; an export-only adaptation removed the host iframe and unused helper dependencies and embedded the bundled Lucide library. No web server or Codex host is required to open the resulting walkthrough. Design controls supplied by Codex are not part of the standalone export.

## Verification

- Captured all 18 states at 1024px and 390px, with icons present and no horizontal root overflow.
- Exercised the exported occasion draft/add-wine loop and guest sign-in/save path in headless Edge.
- Observed no script runtime errors or failed network requests during export capture.
- Inspected representative desktop collection/scrapbook and mobile occasion images for full-page capture and legibility.
- Validated DESIGN.md frontmatter, matching canonical/export copies, image dimensions, inventory hashes, and ZIP integrity before delivery.

Stitch import itself has not been performed. Screenshots and static HTML are design references, not an exported .fig file or a promise of lossless editable-component import. Follow the README using the Start with your design UI the user supplied.
