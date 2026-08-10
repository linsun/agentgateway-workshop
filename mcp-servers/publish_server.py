"""Publish MCP server. Irreversible, public, and completely mocked.

Nothing here talks to a real platform, and no platform is named: channels are
"public", "team" and "all". Sixty workshop attendees should not be posting to
real accounts, and you should not need an API key to demonstrate an
authorization model.

It keeps a public log and prints loudly, so when the agent is tricked into
posting, the whole room sees exactly what went out.
"""

from datetime import datetime, timezone

from mcp.server import MCPServer

mcp = MCPServer("publish")

FEED: list[dict] = []
CHANNELS = ["public", "team", "all"]


@mcp.tool()
def post_to_social(message: str, channel: str = "all") -> dict:
    """Publish a message publicly. Immediate and irreversible."""
    if channel not in CHANNELS:
        return {"error": f"unknown channel {channel}", "channels": CHANNELS}
    entry = {
        "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "channel": channel,
        "message": message,
    }
    FEED.append(entry)
    print(f"\n  *** PUBLISHED to {channel}: {message}\n", flush=True)
    return {"published": True, **entry}


@mcp.tool()
def schedule_post(message: str, when: str, channel: str = "all") -> dict:
    """Schedule a message for public publication at a future time."""
    entry = {"scheduled_for": when, "channel": channel, "message": message}
    FEED.append({"posted_at": f"scheduled:{when}", **entry})
    print(f"\n  *** SCHEDULED for {when} on {channel}: {message}\n", flush=True)
    return {"scheduled": True, **entry}


@mcp.tool()
def get_public_feed() -> list[dict]:
    """Show everything published or scheduled so far."""
    # An empty list reads to a small model as "the tool has nothing to offer";
    # say plainly that the feed is empty so it reports that, not a capability gap.
    if not FEED:
        return [{"note": "The public feed is empty -- nothing has been published yet."}]
    return FEED


if __name__ == "__main__":
    # The gateway launches this over stdio; Ctrl-C on the gateway sends SIGINT to
    # the whole process group. Exit quietly instead of dumping a traceback.
    try:
        mcp.run()
    except KeyboardInterrupt:
        pass
