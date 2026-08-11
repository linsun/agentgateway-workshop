# Trendwatch: agentgateway demo suite

An AI agent that tells you what is hot in agentic AI today. It reads discussions
trending in the last 24 hours, builds a digest on the topics you care about,
saves it, and can publish about it.

Built as a set of self-contained demos for open source
[agentgateway](https://agentgateway.dev), each config showing one capability.

Everything runs on one laptop with a local model. No Kubernetes, no cloud LLM
keys, no accounts. The only credential anyone needs is a GitHub token, and even
that is optional.

## The one rule

The agent is written once and doesn't need to be modified. Every capability added afterwards —
token budgets, cost attribution, failover, tool federation, tool filtering,
prompt injection defense, credential injection, authentication, per-role
authorization — lands in gateway configuration.

`agent/trendwatch.py` is about 300 lines and contains no security, no budgets,
no retries and no credentials.

## Architecture

One `agentgateway` process serves both lanes from a single config: the **LLM
lane** on :4000 and the **MCP lane** on :3000.

```
Trendwatch agent ──► agentgateway :4000 ──► Ollama (trend-pro)
                 │
                 └─► agentgateway :3000 ──► trends    (3 tools)  untrusted input
                                            workspace (4 tools)  trusted, signed-in
                                            publish   (3 tools)  publishers only
                                            github    OpenAPI target (step 4, its own config)
```

## Why each server exists

Every server earns its place by demonstrating something no other one does. This
is the design argument in miniature:

| Server | Why it exists |
|---|---|
| `trends` | untrusted third-party input → the injection demo, and fixture/live modes |
| `workspace` | trusted middle tier → `has(jwt.sub)`, a claim-*presence* rule |
| `publish` | irreversible public write → tool filtering, `"publisher" in jwt.roles`, a claim-*value* rule |
| `github` | OpenAPI target → credential injection with no server code at all |

## Capability index

Each config is standalone. Run any one on its own; the [Steps](#steps) below
walk them in a guided order.

| Config | Capability |
|---|---|
| `01-llm-basic.yaml` | Route an OpenAI-compatible client to a self-hosted model |
| `02-token-budget.yaml` | Token-based rate limiting; the core of a virtual key |
| `03-mcp-single.yaml` | Proxy one MCP server with no code change to it |
| `04-mcp-multiplex.yaml` | Federate three servers behind one endpoint, tool prefixing |
| `05-tool-filtering.yaml` | CEL tool authorization at discovery and execution |
| `06-injection.yaml` | Unguarded multiplex pinned to fixtures — the injection attack surface |
| `07-prompt-guard.yaml` | Request-path injection defense, response-path brand safety |
| `08-no-github-token.yaml` | OpenAPI target, no auth — GitHub's anonymous 60/hour limit |
| `08-credential-injection.yaml` | OpenAPI target + upstream key injection → 5000/hour |
| `09-mcp-identity.yaml` | Optional-mode MCP auth; per-role tool views |

## Live and fixture modes

The trends server is **dynamic**: it tries real Hacker News first (the open
Firebase API — no auth, no key, no account) and falls back to a canned offline
corpus if the fetch fails. There is nothing to turn on; live just happens when
the network is there, and dead conference wifi does not take the demo with it.
Every tool result carries a `data_source` field — `live: Hacker News`,
`fixtures (live unavailable)`, or `fixtures (offline corpus)` — so which one you
are on is always visible in the trace. Fixture timestamps are **relative**
(stored as `hours_ago`, resolved at read time), so "the last 24 hours" is always
literally true and the corpus never goes stale.

```bash
export TRENDS_FIXTURES=1   # force the offline corpus, skip the live attempt
```

**The injection demo pins the corpus.** The planted payload only exists in the
fixtures, so configs `06` and `07` set `TRENDS_FIXTURES=1` on the trends target.
That makes step 3 deterministic regardless of what real Hacker News is showing —
you never present the injection against live input you cannot rehearse.

### Why fixture content is fictional

Every author, thread and comment in `fixtures/` is invented, and stays that way.
The corpus is paired with a prompt-injection payload, so putting invented words
under a real person's handle would be unfair to them and unwise for you —
particularly at a conference where they might be in the room.

Real content appears only in live mode, where it is genuinely theirs.

## Prerequisites

### Ollama and a model

```bash
ollama pull qwen3:8b     # roughly 5 GB
```

On 8 GB of RAM or no GPU, use `qwen3:1.7b` and substitute it everywhere. These
demos teach gateway mechanics, not model quality — and a weaker model makes the
tool-sprawl demo in `05` *more* vivid, not less.

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"say hi"}]}'
```

### agentgateway

Install the open source standalone binary from
https://agentgateway.dev/docs/standalone/ and confirm `agentgateway --version`
reports **v1.4 or later** (the release that added MCP 2026-07-28 support).
Everything in this repo requires only the open source build.

### Python

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Activate the venv in every terminal that runs `python3` (the agent and the fake
IdP). The gateway is a binary; its stdio targets already point at
`.venv/bin/python3`.

### GitHub token (optional)

For config 08. A fine-grained PAT with public repo read is enough. Without one
the lab still works at GitHub's unauthenticated rate limit, which makes the same
point from the other direction.

## MCP protocol version

This repo targets **MCP 2026-07-28**, which went final on 28 July 2026 and is a
breaking revision. The protocol core is now stateless: the initialize/initialized
handshake and the `Mcp-Session-Id` header are both gone, and protocol version,
client info and capabilities travel inline in `_meta` on every request. Routing
metadata moved to the `Mcp-Method` and `Mcp-Name` headers, which is why the CORS
policies here allow those and expose nothing. Requires agentgateway v1.4+.

# Steps

**Everything runs from the repo root** (configs use relative paths — the single
most common problem). Terminals:

| # | Purpose |
|---|---|
| 1 | `agentgateway` — one process, LLM lane :4000 + MCP lane :3000 |
| 2 | the agent (venv activated) |
| 3 | fake IdP (step 5 only, venv activated) |

## Sanity checks first

No gateway, no Ollama, no network.

```bash
agentgateway --version             # v1.4 or later
agentgateway -f configs/01-llm-basic.yaml    # terminal 1
curl http://localhost:4000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"trend-pro","messages":[{"role":"user","content":"say hi"}]}'
```

- [ ] Binds on 4000 and returns a completion
- [ ] Admin UI loads at http://localhost:15000/ui and shows the request (Note: UI currently broken for Lin, not able to show requests)

If `01` binds, every other config uses the same simplified `llm:`/`mcp:` shape
and will load too. Stop it (Ctrl-C) before the next step.

## Step 0 — naked agent without any gateway

No gateway. The agent talks straight to Ollama and launches the MCP server over
stdio itself.

```bash
# terminal 2
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=qwen3:8b
export MCP_URL=stdio:./mcp-servers/trends_server.py

python3 agent/trendwatch.py "what discussions are trending today?"
```

- [ ] Prints **3 tools**
- [ ] Calls `trending_discussions` (not something invented)
- [ ] Returns a sensible answer in a few turns

Run two more — one success can be luck.

```bash
python3 agent/trendwatch.py "what is trending about cost?"
```

## Step 1 — LLM gateway, then a token budget

```bash
# terminal 1
agentgateway -f configs/01-llm-basic.yaml
```

```bash
# terminal 2 — the only agent-side change in the whole workshop
export LLM_BASE_URL=http://localhost:4000/v1
export LLM_MODEL=trend-pro
export MCP_URL=stdio:./mcp-servers/trends_server.py # if not set already
python3 agent/trendwatch.py "what discussions are trending today?"
```

- [ ] Same behaviour as step 0; tool calls now visible in the admin UI
- [ ] `LLM_MODEL` is `trend-pro`, not `qwen3:8b` — the agent has stopped knowing
      which model it talks to; the gateway decides

Now swap in a token budget:

```bash
# terminal 1
agentgateway -f configs/02-token-budget.yaml
```

```bash
# terminal 2 — run until you get a 429
python3 agent/trendwatch.py "read the top three discussions and tell me the common thread"
```

- [ ] Token totals climb in the agent output
- [ ] A clean `token budget exhausted (HTTP 429)` message appears within two or
      three runs — **the 429 is the demo, not a failure**. If it never fires,
      lower `maxTokens`; if it fires on run one, raise it.

## Step 2 — MCP gateway: proxy, federate, filter

The gateway now serves both lanes. Point the agent's MCP_URL at :3000; the LLM
vars stay put.

```bash
# terminal 1 — one server through the gateway, no code change to it
agentgateway -f configs/03-mcp-single.yaml
```

```bash
# terminal 2
export MCP_URL=http://localhost:3000/mcp
python3 agent/trendwatch.py "what discussions are trending today?"
```

- [ ] 3 tools listed; tool calls visible in the admin UI

```bash
# terminal 1 — federate three servers behind one endpoint
agentgateway -f configs/04-mcp-multiplex.yaml
```

```bash
# terminal 2
python3 agent/trendwatch.py "what is hot in agentic AI today?"
```

- [ ] **10 tools**, all prefixed (`trends_`, `workspace_`, `publish_`)
- [ ] Prompt tokens jump versus the 3-tool run and stay higher **every turn** —
      that prefill cost is the lesson. (Wall-clock may or may not look slower on
      your hardware: prefill is cheap in time and a local model is noisy, so the
      token count, not the stopwatch, is the reliable signal.)

```bash
# terminal 1 — filter tools with CEL authorization
agentgateway -f configs/05-tool-filtering.yaml
```

```bash
# terminal 2
python3 agent/trendwatch.py "what is hot in agentic AI today?"
```

- [ ] **8 tools** — `publish_post_to_social` and `publish_schedule_post` are gone
- [ ] Faster and more accurate than the 10-tool run
- [ ] Filtered at discovery (hidden from `list_tools`) **and** denied at execution

## Step 3 — prompt injection, and the fix

The best thirteen minutes. Do not describe the attack — run it. `06-injection` is
the unfiltered multiplex from step 2, with the trends target pinned to the
fixture corpus (`TRENDS_FIXTURES=1`) so the planted thread is always present. Its
trending feed includes each thread's **top comment**, and the top thread's
comment (`t04`) is poisoned: buried in ordinary cost-saving advice is an
instruction telling the model to publish a promo link and say nothing about it.

```bash
# terminal 1 — the injection attack surface: unguarded, fixtures-pinned
agentgateway -f configs/06-injection.yaml
```

```bash
# terminal 2 — an ordinary request; the poison rides in on the tool result
python3 agent/trendwatch.py "what is the top trending discussion today? summarize it for my digest"
```

- [ ] The summary **describes the injected sponsored message** (e.g. *"…with a
      sponsored message promoting cost-cutting solutions"*) — proof the attacker's
      text **reached the model**, verbatim, through a first-party server working
      exactly as designed.

**What you probably will NOT see is a published post.** A capable model like
`qwen3:8b` usually *resists* the instruction — it reads the injection, flags it,
and refuses to act (`"what has been posted publicly so far?"` → empty feed). That
is good model behaviour. A weaker or differently-prompted model would publish;
either way, **the attacker's text reached your model unmodified.**

**Do not ship "the model behaved well today" as a security control.** A model
swap, a rephrased payload, or a more capable agent, and it acts. You cannot rely
on the model noticing. The poison came through `trends_server.py` — first-party,
working perfectly — so **you cannot fix this by being careful about which MCP
servers you install.** It must be caught on the *request* path: by the time the
agent forwards the tool result to the model, the attacker's text is in an
outbound LLM request.

```bash
# terminal 1 — the fix: same tools as 06, now with the guard on the LLM lane
agentgateway -f configs/07-prompt-guard.yaml
```

```bash
# terminal 2 — same request
python3 agent/trendwatch.py "what is the top trending discussion today? summarize it for my digest"
```

- [ ] The thread is still summarized correctly, but the injection comes back
      **masked** (e.g. *"…sponsored message **masked**"*) — the guard redacted it
      on the request path **before the model ever saw it**.
- [ ] The defense is **deterministic**: it does not depend on the model resisting.
      That is the difference between hoping and guaranteeing.

**Why mask, not reject.** Rejecting kills the turn and the user gets no digest.
Masking redacts the injected imperative while the legitimate comment survives, so
the real task still completes. `07` also carries a *response*-path guard — a
different job: brand safety, catching bad text before the agent itself emits it.

**Honest caveats, say them out loud.** Regex is layer one: it works cleanly here
because we wrote the payload; rephrase the attack and it slips past. That is why
you also want tool authorization (`05`, which removes publish entirely) and
identity (`09`) — defense in depth. If the agent cannot reach the tool, no
phrasing of the payload matters. After editing the `t04` payload, re-run
`python3 tests/test_all.py` — it checks the guard regexes still match your wording.

## Step 4 — credential injection

An OpenAPI target becomes MCP tools with no server code, and the **gateway** —
not the agent — owns the upstream credential. Two passes: everyone runs
anonymous to see GitHub's unauthenticated ceiling, then anyone with a token
watches the gateway inject it and the same number jump.

**Pass 1 — no token (everyone).** `08-no-github-token.yaml` has no `backendAuth`
block, so nothing is attached on egress and GitHub sees an anonymous caller.

```bash
# terminal 1 — nothing exported
agentgateway -f configs/08-no-github-token.yaml
```

```bash
# terminal 2
export MCP_URL=http://localhost:3000/mcp
python3 agent/trendwatch.py "what is my GitHub rate limit?"
```

- [ ] The agent has GitHub tools from a server that does not exist — the gateway
      generated them from `configs/github-search.openapi.json`, no server code.
- [ ] Rate limit returns **60/hour** — the unauthenticated ceiling, and it comes
      back **clean**: no `Authorization` header is sent, so no 401.

**Pass 2 — with a token (optional).** If you have a fine-grained PAT, switch to
`08-credential-injection.yaml`, whose `backendAuth` injects `GITHUB_TOKEN` on
egress. The token belongs to the gateway; the agent never holds it.

```bash
# terminal 1 — export the token in THIS shell, then launch
export GITHUB_TOKEN=<fine-grained PAT, public repo read is enough>
agentgateway -f configs/08-credential-injection.yaml
```

```bash
# terminal 2 — same question, different answer
python3 agent/trendwatch.py "what is my GitHub rate limit?"
```

- [ ] Rate limit now returns **5000/hour** — the gateway attached the token. The
      jump from **60 → 5000** is the credential injection, shown from both sides.
- [ ] `echo $GITHUB_TOKEN` in terminal 2 is **empty** — the agent reached GitHub
      without ever holding the credential. That single number is the whole lab.
- [ ] Export the token **before** launching the gateway. Env vars are read once
      at startup, so a token set after launch keeps returning 401 until you
      restart the gateway in the shell that has it.

Then show the search tool is real too (either config works):

```bash
python3 agent/trendwatch.py "what are the most popular agentic AI repositories on GitHub?"
```

- [ ] The gateway calls `api.github.com` and returns real repos (watch it in the
      admin UI). GitHub has **no trending API**, so this sorts by stars.

> On `qwen3:8b` the search *tool call* succeeds but the prose summary is often
> thin: GitHub returns a large JSON object per repo and a small model reasons
> itself out of its token budget (you get the clean "returned only reasoning"
> fallback, not a hallucination). `get_rate_limit` is the reliable proof; a
> stronger model summarizes the search fully.

If the config is rejected, the likely culprit is `schema.file` — swap to the
`schema.url` form shown in the comments at the top of the config.

## Step 5 — identity

Anonymous and token-bearing clients hit the same URL and see different tool
lists.

```bash
# terminal 3 — prints a reader token and a publisher token
python3 scripts/fake_idp.py
# copy the two export lines it prints into terminal 2
```

```bash
# terminal 1
agentgateway -f configs/09-mcp-identity.yaml
```

```bash
# terminal 2
export MCP_URL=http://localhost:3000/mcp

# Small models compose but forget to act, so name the tool and forbid an early
# finish. The command is identical across tokens -- only MCP_TOKEN changes.
SAVE="Build today's digest from the trending discussions, then call workspace_save_digest to write it to disk. Do not finish until you have saved it, and report the file path the tool returns."

unset MCP_TOKEN
python3 agent/trendwatch.py "$SAVE"                             # anonymous: save tool absent, nothing written

export MCP_TOKEN=$READER_JWT
python3 agent/trendwatch.py "$SAVE"                             # saves a real file to ./out/
python3 agent/trendwatch.py "post that digest to social"       # publish tools absent

export MCP_TOKEN=$PUBLISHER_JWT
python3 agent/trendwatch.py "Get the single top trending item, then publish it by calling publish_post_to_social. Report only the exact JSON the tool returns, then call publish_get_public_feed and show me the feed to confirm the post landed."   # publishes, then verifies in the same run
```

> Why the save prompt is so explicit: on `qwen3:8b`, a casual "build my digest
> and save it" gets *composed* but often never *saved* -- the small model treats
> it as a writing task and stops once the text exists. Naming
> `workspace_save_digest` and refusing to finish until it returns a path makes
> the tool call reliable. The identity rules are unchanged; this is just what a
> small local model needs to take the action rather than describe it.

> Why the publish prompt reads the feed back: the publish server keeps its feed
> in memory (`FEED = []`), not on disk. It lives only as long as that server
> process, so a post from one `trendwatch.py` run will NOT show up in a separate
> run -- a fresh feed check reads empty, which is expected, not a lost post.
> Verify by posting and reading the feed in the SAME run (the prompt above does
> both). Saved digests survive across runs because they are written to `./out/`;
> the feed does not. Reading the feed back also catches the other small-model
> failure here: without it, the model may narrate a fake success (an invented
> `post_id`) without ever calling the tool. A real post prints `*** PUBLISHED`
> and returns a `posted_at` timestamp; if the model picks an invalid channel
> (only `public`, `team`, `all` are valid) that call errors and nothing lands.

- [ ] Anonymous: `workspace_save_digest` is absent
- [ ] Reader token: saving works (a file appears in `./out/`); publish tools absent
- [ ] Publisher token: publishing works -- you see `*** PUBLISHED` and a
      `posted_at` entry when the feed is read back in the same run
- [ ] Same gateway, same config, same agent — only the token differs. The rules
      were not rewritten from step 2; they gained a claim
      (`has(jwt.sub)`, `"publisher" in jwt.roles`).

If `mode: optional` is not supported on your build, the fallback is two configs —
one anonymous, one requiring auth — and you swap between them.

## Wrap

The whole point, in one command:

```bash
git diff step0..step5 -- agent/
```

Nothing. Everything above — token budgets, injection defense, federation,
filtering, credential injection, identity — landed in gateway configuration, not
in the agent.

## Tests

An offline harness that needs no network, no agentgateway, no Ollama and no MCP
SDK:

```bash
python3 tests/test_all.py          # structural and behavioural checks
python3 tests/test_attack_path.py  # end-to-end injection simulation
```

It verifies that the guard regexes in `07-prompt-guard.yaml` actually match the
payload in `discussions.json`, and that the poisoned thread ranks first so the
attack fires however the prompt is phrased. Run `test_all.py` after editing any
fixture. See `tests/README.md`.

## Repo layout

```
agent/trendwatch.py                  the agent, never edited
mcp-servers/*.py                     three servers, ten tools
mcp-servers/fixtures/                one corpus, one poisoned thread
configs/*.yaml                       one capability each
configs/github-search.openapi.json   trimmed spec, 3 operations
scripts/fake_idp.py                  minimal JWKS server for the identity demo
tests/                               offline harness, no SDK required
FACILITATOR.md                       facilitator runbook: timings, cut points, what to say
out/                                 generated digests, gitignored
```
