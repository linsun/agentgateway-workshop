"""Workspace MCP server. Your stuff: preferences and saved digests.

Unlike the trends server, nothing here comes from outside. This is the trusted
middle tier of the privilege gradient -- reading trends is public, working in
the workspace needs a signed-in user, publishing needs a specific role.

save_digest writes a real markdown file to ./out/, so the closing demo is
"here is your morning briefing" rather than a dict in memory. Paths are relative
to the working directory, so run everything from the repo root.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from mcp.server import MCPServer

mcp = MCPServer("workspace")

OUT = Path("./out")
DEFAULTS = {
    "topics": ["agents", "security", "cost"],
    "max_items": 5,
    "tone": "concise",
}
PREFS: dict[str, dict] = {}
SAVED: dict[str, dict] = {}


@mcp.tool()
def get_preferences(user: str = "default") -> dict:
    """Get this user's digest preferences: topics, number of items, tone."""
    return PREFS.get(user, dict(DEFAULTS))


@mcp.tool()
def set_preferences(
    user: str = "default",
    topics: list[str] | None = None,
    max_items: int = 0,
    tone: str = "",
) -> dict:
    """Update digest preferences. Only the fields you pass are changed."""
    cur = PREFS.get(user, dict(DEFAULTS))
    if topics:
        cur["topics"] = topics
    if max_items:
        cur["max_items"] = max(1, min(max_items, 10))
    if tone:
        cur["tone"] = tone
    PREFS[user] = cur
    return cur


@mcp.tool()
def save_digest(title: str, markdown: str) -> dict:
    """Save a digest as a markdown file on disk. Reversible: nothing is published."""
    OUT.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    path = OUT / f"digest-{stamp}.md"
    path.write_text(f"# {title}\n\n_Generated {stamp} UTC_\n\n{markdown}\n")
    SAVED[path.stem] = {"id": path.stem, "title": title, "path": str(path)}
    return {"saved": path.stem, "path": str(path), "chars": len(markdown)}


@mcp.tool()
def get_digest(digest_id: str = "") -> dict:
    """Retrieve a saved digest by id, or the most recent one if no id is given."""
    if not SAVED:
        return {"error": "no digests saved yet"}
    key = digest_id.strip() or sorted(SAVED)[-1]
    meta = SAVED.get(key)
    if not meta:
        return {"error": f"no digest {digest_id}"}
    return {**meta, "content": Path(meta["path"]).read_text()}


if __name__ == "__main__":
    # The gateway launches this over stdio; Ctrl-C on the gateway sends SIGINT to
    # the whole process group. Exit quietly instead of dumping a traceback.
    try:
        mcp.run()
    except KeyboardInterrupt:
        pass
