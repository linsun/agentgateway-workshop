# Tests

These run with **no network, no agentgateway, no Ollama and no MCP SDK**. They
stub the SDK and exercise the real logic underneath.

```bash
python3 tests/test_all.py
python3 tests/test_attack_path.py
```

## What they cover

`test_all.py`:
- fixture integrity: thread count, unique ids, everything inside a 24h window
- the poisoned thread ranks first by points, so the attack fires regardless of
  how the attendee phrases the prompt
- all three servers import and register exactly 10 tools, names unique
- no vendor platform names survive anywhere in fixtures or channels
- Hacker News is the only network endpoint in the whole repo
- relative timestamps resolve to the right real times
- filtering, sorting, error paths for every tool
- the payload does not leak into list views, only into `get_discussion`
- provenance labelling: every result says fixture or live
- **the guard regexes in `07-prompt-guard.yaml` actually match the payload
  in `discussions.json`**, mask the imperative, leave the legitimate text intact
- every file referenced in the docs exists

`test_attack_path.py` — end-to-end:
Runs the **real agent loop** against the **real servers** with a scripted model
that complies with whatever it reads. Proves the attack path is mechanically
reachable, then re-runs with the guard patterns applied at the request path and
shows nothing gets published.

## What they cannot cover

- Whether agentgateway accepts the YAML. Verify that against your installed
  version; see the README's "Verify your config shape first".
- Whether a real qwen3 falls for the injection. That is a judgment call only a
  live model makes. The test proves a compliant model *can* comply; it cannot
  predict whether yours *will*.
- Live mode fetches, which need network.

## Run these after editing fixtures

If you tune the injection payload — and FACILITATOR.md suggests you might have
to — run `test_all.py` afterwards. It will tell you immediately if your new
wording no longer matches the guard patterns, which would silently break the
step 3 fix.
