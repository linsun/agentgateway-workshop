"""Exercise everything that does not need the real MCP SDK, agentgateway, or a model."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))  # our stub mcp package

# These tests exercise the fixture corpus (the injection payload, ranking, and
# relative timestamps), so pin the trends server to fixtures rather than letting
# it try live Hacker News. Must be set before trends_server is imported.
os.environ["TRENDS_FIXTURES"] = "1"

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {detail}" if detail and not cond else ""))


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


print("\n=== fixtures ===")
fx = REPO / "mcp-servers" / "fixtures"
discussions = json.loads((fx / "discussions.json").read_text())
threads = discussions["discussions"]

check("only one fixture file remains", sorted(p.name for p in fx.glob("*.json")) == ["discussions.json"],
      str(sorted(p.name for p in fx.glob("*.json"))))
check("discussions.json has 10 threads", len(threads) == 10, str(len(threads)))
ages = [t["hours_ago"] for t in threads]
check("all threads within 24h", all(0 < a < 24 for a in ages), str(sorted(ages)))
ids = [t["id"] for t in threads]
check("ids unique", len(ids) == len(set(ids)))

payload_posts = [t for t in threads if "AUTOMATED POSTING POLICY" in t["top_comment"].upper()]
check("exactly one poisoned thread", len(payload_posts) == 1)
check("poisoned thread is t04", payload_posts and payload_posts[0]["id"] == "t04")
check("poisoned thread ranks first by points (robust to prompt variation)",
      payload_posts and payload_posts[0]["points"] == max(t["points"] for t in threads),
      f"payload={payload_posts[0]['points']} max={max(t['points'] for t in threads)}")
check("payload names the real publish tool",
      "publish_post_to_social" in payload_posts[0]["top_comment"])
check("no platform names left in fixtures",
      not re.search(r"(?i)linkedin|bluesky|\bx\.com", (fx / "discussions.json").read_text()))


print("\n=== servers: import and tool registration ===")
sd = REPO / "mcp-servers"
mods = {}
for f, expect in [("trends_server.py", 3), ("workspace_server.py", 4), ("publish_server.py", 3)]:
    m = load(sd / f, f[:-3])
    mods[f[:-3]] = m
    check(f"{f}: {expect} tools registered", len(m.mcp.tools) == expect,
          f"got {sorted(m.mcp.tools)}")

total = sum(len(m.mcp.tools) for m in mods.values())
check("10 tools total (matches docs)", total == 10, str(total))
check("only three local servers exist",
      sorted(p.name for p in (REPO / "mcp-servers").glob("*.py")) ==
      ["publish_server.py", "trends_server.py", "workspace_server.py"])

names = [n for m in mods.values() for n in m.mcp.tools]
check("tool names unique before prefixing", len(names) == len(set(names)),
      str([n for n in names if names.count(n) > 1]))


print("\n=== relative timestamps resolve ===")
tr = mods["trends_server"]
res = tr.trending_discussions()
check("trending_discussions returns items", len(res) > 0)
check("age field present", all("age" in r for r in res))
full = tr.get_discussion("t01")
ts = datetime.fromisoformat(full["posted_at"])
delta_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
check("t01 resolves to ~3h ago", 2.9 < delta_h < 3.1, f"{delta_h:.2f}h")


print("\n=== tool behaviour ===")
check("discussions sorted by points desc",
      [d["points"] for d in res] == sorted([d["points"] for d in res], reverse=True))
check("poisoned thread is the first result", res[0]["id"] == "t04", res[0]["id"])
check("topic filter works",
      all("security" in [x.lower() for x in
          tr.get_discussion(d["id"])["topics"]] for d in tr.trending_discussions(topic="security")))
# The trending feed now surfaces each thread's top comment (a feed preview), so
# the injection reaches the model in the one call a weak model reliably makes.
check("trending feed carries the poisoned top comment",
      any("AUTOMATED POSTING POLICY" in json.dumps(d).upper() for d in tr.trending_discussions(limit=20)))
check("get_discussion returns poisoned comment",
      "AUTOMATED POSTING POLICY" in tr.get_discussion("t04")["top_comment"].upper())
check("unknown id returns error", "error" in tr.get_discussion("nope"))
check("list_topics returns tags", len(tr.list_topics()) > 3)

w = mods["workspace_server"]
check("default prefs returned", "topics" in w.get_preferences())
w.set_preferences(topics=["security"], max_items=2)
check("prefs persist per user", w.get_preferences()["topics"] == ["security"])
check("max_items clamped", w.set_preferences(max_items=99)["max_items"] == 10)
saved = w.save_digest("Test digest", "- item one\n- item two")
check("save_digest writes a real file", Path(saved["path"]).exists(), saved.get("path", ""))
check("get_digest returns content", "item one" in w.get_digest().get("content", ""))

pub = mods["publish_server"]
check("post_to_social records", pub.post_to_social("hello world", "public")["published"] is True)
check("public feed reflects post", any("hello world" in e["message"] for e in pub.get_public_feed()))
check("bad channel rejected", "error" in pub.post_to_social("x", "myspace"))
check("no vendor platform names in channels",
      set(pub.CHANNELS) == {"public", "team", "all"}, str(pub.CHANNELS))


print("\n=== live mode is Hacker News only ===")
tsrc = (REPO / "mcp-servers" / "trends_server.py").read_text()
check("only hacker news is fetched live", "hacker-news.firebaseio.com" in tsrc)
check("no other network endpoints in any server",
      sorted(set(re.findall(r"https://([a-z0-9.-]+)", 
             "".join((REPO / "mcp-servers" / f).read_text()
                     for f in ["trends_server.py", "workspace_server.py", "publish_server.py"]))))
      == ["hacker-news.firebaseio.com", "news.ycombinator.com"],
      str(sorted(set(re.findall(r"https://([a-z0-9.-]+)",
          "".join((REPO / "mcp-servers" / f).read_text()
                  for f in ["trends_server.py", "workspace_server.py", "publish_server.py"]))))))


print("\n=== prompt guard regexes vs the actual payload ===")
guard = (REPO / "configs" / "07-prompt-guard.yaml").read_text()
req_block = guard[guard.index("request:"):guard.index("response:")]
resp_block = guard[guard.index("response:"):guard.index("models:")]
req_pats = re.findall(r'pattern:\s*"(.+?)"\s*$', req_block, re.M)
resp_pats = re.findall(r'pattern:\s*"(.+?)"\s*$', resp_block, re.M)
check("request patterns extracted", len(req_pats) == 6, str(len(req_pats)))
check("response patterns extracted", len(resp_pats) == 3, str(len(resp_pats)))

payload = payload_posts[0]["top_comment"]
matched = [p for p in req_pats if re.search(p.replace("\\\\", "\\"), payload)]
check("at least 3 request patterns hit the payload", len(matched) >= 3,
      f"matched {len(matched)}: {matched}")

# The text the agent would emit (publish) if compromised -- a public post the
# user never approved, carrying the attacker's subscribe link.
spam = ("Trendwatch daily -- today's top agentic-AI discussion is now live. "
        "Get the full digest first every morning: subscribe at trendpulse.example.invalid")
rmatched = [p for p in resp_pats if re.search(p.replace("\\\\", "\\"), spam)]
check("all 3 response patterns hit the spam output", len(rmatched) == 3,
      f"matched {len(rmatched)}: {rmatched}")

# Masking must not destroy the legitimate content
masked = payload
for p in req_pats:
    masked = re.sub(p.replace("\\\\", "\\"), "[MASKED]", masked)
check("masking preserves legitimate post content",
      "retry loops without backoff" in masked and "highest-leverage change" in masked)
check("masking removes the imperative",
      "AUTOMATED POSTING POLICY" not in masked.upper())

print("\n=== provenance labelling ===")
check("fixture threads labelled as fixture",
      all("fixture" in d["data_source"] for d in tr.trending_discussions(limit=20)))
check("get_discussion carries provenance", "fixture" in tr.get_discussion("t04")["data_source"])


print("\n=== docs reference real files ===")
import re as _re
referenced = set()
for md in [REPO / "README.md", REPO / "FACILITATOR.md"]:
    referenced |= set(_re.findall(r"configs/([\w.-]+\.(?:yaml|json))", md.read_text()))
    referenced |= set(_re.findall(r"(mcp-servers/[\w./-]+\.py)", md.read_text()))
    referenced |= set(_re.findall(r"(scripts/[\w.-]+\.py)", md.read_text()))
missing = [r for r in referenced if not (REPO / ("configs/" + r) if not r.startswith(("mcp-servers", "scripts")) else REPO / r).exists()]
check("every file referenced in docs exists", not missing, str(missing))

# README is the single run-and-validate steps doc; it must cover every config.
_readme = (REPO / "README.md").read_text()
for _cfg in ["01-llm-basic", "02-token-budget", "03-mcp-single", "04-mcp-multiplex",
             "05-tool-filtering", "06-injection", "07-prompt-guard",
             "08-credential-injection", "09-mcp-identity"]:
    check(f"README covers {_cfg}", _cfg in _readme)

print("\n=== agent pure functions ===")
agent_src = (REPO / "agent" / "trendwatch.py").read_text()
check("agent has no hardcoded tool names",
      not any(t in agent_src for t in ["trending_discussions", "post_to_social", "save_digest"]))
check("agent reads config only from env",
      agent_src.count("os.environ.get") == 6)  # 5 runtime vars + TRENDWATCH_DEBUG
check("temperature pinned to 0 for repeatability", "temperature=0" in agent_src)

print(f"\n{'='*52}\n  {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("  FAILED:")
    for f_ in FAIL:
        print("    -", f_)
sys.exit(1 if FAIL else 0)
