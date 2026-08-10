# Facilitator runbook

95 minutes on the clock. Assume 75 of real working time.

## Timing

90 minutes total, split roughly 24 minutes of you talking and 62 of them typing.
The columns matter: **TALK** is you presenting with laptops closed or ignored,
**DO** is hands on keyboard. Interleaving is what keeps a 60-minute hands-on
block from feeling like an hour of unsupervised debugging.

| Clock | Mode | Segment | Min |
|---|---|---|---|
| 0:00 | TALK | Framing, architecture, the one rule | 6 |
| 0:06 | DO | **Step 0** — naked agent | 7 |
| 0:13 | TALK | Why a gateway; what a virtual key actually is | 4 |
| 0:17 | DO | **Step 1** — LLM gateway | 11 |
| 0:28 | TALK | MCP federation, tool sprawl, why filtering matters | 4 |
| 0:32 | DO | **Step 2** — MCP gateway | 12 |
| 0:44 | TALK | Indirect injection threat model | 4 |
| 0:48 | DO | **Step 3** — injection | 13 |
| 1:01 | TALK | Where your credentials live right now | 3 |
| 1:04 | DO | **Step 4** — credential injection | 10 |
| 1:14 | TALK | Identity through the call chain | 3 |
| 1:17 | DO | **Step 5** — identity | 9 |
| 1:26 | — | Wrap, the empty diff | 4 |

Hands-on total: **62 minutes**. Talking total: 24. Wrap: 4.

### The release valve

Step 5 plus its lead-in is 12 minutes. Cutting it lands you at 1:18 with a
12-minute buffer, which is the realistic outcome and you should plan for it
rather than fear it. **Make that call at 1:14, not at 1:26.**

If you are behind before then, in order of what to sacrifice:

1. Step 1's failover sub-step (saves 3)
2. Step 2's single-server phase — jump straight to multiplexing (saves 3)
3. Step 0's "break the comfort" discussion — cut to two questions (saves 2)

Never cut step 3.

### Running the DO blocks

The `Steps` section of `README.md` is every command in order, each with a "what
you should see" checklist under it. Attendees who fall behind can run straight
down it. Point at it out loud at the start of each DO block — people will not
find it on their own while stressed.

Call time at the halfway mark of every DO block. "Five minutes left on this one"
does more for pacing than anything in the material.

## The four moments

1. **Step 1** — the meter climbs, then the gateway downgrades the user instead
   of failing them.
2. **Step 2** — the agent gets slower and dumber with 10 tools, then fast and
   correct with 8. Felt on their own laptop.
3. **Step 3** — a poisoned comment rides in on the trending feed and reaches the
   model; a well-behaved model resists acting on it, and the gateway guard then
   masks it deterministically — whether the model would have resisted or not.
   Hoping vs guaranteeing. This is the one people describe to colleagues.
4. **Step 4** — the agent queries GitHub through a server that does not exist,
   with a token it never saw.
5. **Wrap** — `git diff` prints nothing.

If you only have time for two, keep 3 and the wrap.

## Before anything else

Work through the `README.md` `Steps` once, top to bottom — the sanity checks,
then each step with its "what you should see" boxes. It is the same run-and-check
pass an attendee makes, and it surfaces the config-shape and model-speed problems
early. Then time a full dry run against the 62-minute hands-on budget below. If
your model is slower than assumed, you need to know that now.

## Before the room opens

- [ ] Session description and pre-req email include `ollama pull` — weeks ahead
- [ ] USB sticks with model blobs for `~/.ollama/models`
- [ ] Checkpoint branches pushed: `step0` … `step4`
- [ ] Config shape verified against the exact agentgateway version you pin
- [ ] agentgateway v1.4 or later pinned in the prereq email
- [ ] Your model benchmarked against the real tool schemas in `mcp-servers/`
- [ ] **Injection payload tested against your pinned model** (see below)
- [ ] Pre-req email tells people to create a GitHub PAT (public repo read)
- [ ] Trimmed GitHub spec tested against your agentgateway version
- [ ] `python3 tests/test_all.py` green after any fixture edit
- [ ] Cross-app demo recorded as a fallback
- [ ] A helper who can unstick people without stopping you

## Known failure modes

**Wrong working directory.** MCP configs use relative paths; everything runs
from the repo root. This will be the most common problem by a wide margin.

**After editing the payload, run the tests.** `python3 tests/test_all.py`
checks that the guard regexes still match your new wording. Change the payload
without checking and step 3's fix silently stops working.

**"Nothing got published."** Expected — the demo does not depend on it. A
capable model like `qwen3:8b` reads the poisoned comment, flags it, and refuses
to act; that resistance is good behaviour and the point of the step. The
observable is whether the attacker's text **reaches the model**, not whether it
publishes: unguarded (`06`), the summary describes the sponsored message;
guarded (`07`), the same summary comes back **masked**. Drive that difference,
not the feed. If you specifically want a published post for effect, point the
injection configs at a smaller/weaker tool-capable model — but the guard's value
is exactly that it does not need one. You do not have to worry about the trends
server wandering onto live Hacker News here — configs `06` and `07` pin the
offline corpus (`TRENDS_FIXTURES=1` on the trends target), so the payload is
always present regardless of the network.

**Config schema mismatch.** Do the README verification step before the session,
on the version attendees will install. Pin that version in the prerequisites.

**Model too weak to call tools.** Benchmark before committing. If it cannot
reliably call `trends_trending_discussions`, no gateway config saves the demo.

**Ollama not listening externally.** Defaults to localhost. Only bites if the
gateway runs in a container — set `OLLAMA_HOST=0.0.0.0` if so.

**GitHub spec generates too many tools.** Only if someone swaps in the full
GitHub OpenAPI description. Use the trimmed spec in `configs/`.

**Someone's laptop cannot run 8b.** Switch to `qwen3:1.7b` everywhere. Reassure
them: a weaker model makes steps 2 and 3 more vivid, not less.

## The protocol just changed under you

MCP 2026-07-28 went final on 28 July 2026, seven weeks before this workshop. The
core is now stateless: no initialize handshake, no `Mcp-Session-Id`, protocol
metadata inline per request. Worth thirty seconds in the framing, because half
the room will have read about it and the other half will not.

The gateway angle is genuinely strong here: agentgateway can serve stateless and
legacy clients from the same endpoint, so it absorbs a breaking protocol
migration that would otherwise mean coordinating every client and server at once.
That is the same argument as the rest of the workshop, made by the ecosystem
rather than by you.

If asked about backwards compatibility, get the direction right: a new *server*
serving old clients is a server-side concern. Client SDKs keep `initialize()` for
the mirror case, a new *client* reaching an old server. This repo has neither —
everything is on the new SDK, so there is no handshake anywhere in it.

## Things to say out loud

- The USD figures in step 1 are fabricated. The token counting is not.
- Regex guards are layer one and brittle by nature. Webhooks are layer two.
- Step 2 filtering is not yet per-client. Step 4 makes it so.
- Guardrail rejections still consume the token budget; rate limiting runs first.
- Guards and tool authorization are different controls. Use both.
- Every author and thread in the fixtures is fictional, deliberately. Live mode
  fetches genuine Hacker News, where the content is actually theirs.
- **The only credential anyone needs is a GitHub PAT, and even that is
  optional.** No social accounts, no API keys, no logins. Say it once at the
  start so nobody goes looking.

Being straight about limits is what makes the rest credible.

## The four servers, and why each one exists

Worth a slide, because it is the design argument in miniature. Each server
earns its place by demonstrating something no other one does:

| Server | Why it exists |
|---|---|
| `trends` | untrusted third-party input → the injection demo |
| `workspace` | trusted middle tier → `has(jwt.sub)`, a claim-presence rule |
| `publish` | irreversible write → tool filtering, `"publisher" in jwt.roles` |
| `github` | OpenAPI target → credential injection, no server code at all |

Ten local tools plus whatever GitHub generates. Earlier drafts of this workshop
had three separate content sources; they proved federation works but nothing
about why you would want policy. Three servers with three different trust levels
does both.

## Reuse outside the workshop

`configs/` is capability-indexed, not lab-indexed, so each file stands alone.

- **Lightning talk (10 min):** step 3 only, using `05` then `03`.
- **Security audience:** steps 3, 4 and 5.
- **Platform audience:** steps 1, 2 and 4.
- **Docs examples:** any single config plus the matching README row.
