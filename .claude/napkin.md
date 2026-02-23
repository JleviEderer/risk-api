# Napkin

## Corrections
| Date | Source | What Went Wrong | What To Do Instead |
|------|--------|----------------|-------------------|
| 2026-02-22 | self | Used `setuptools.backends._legacy:_Backend` as build-backend | Use `setuptools.build_meta` — the `_legacy` backend doesn't exist |
| 2026-02-22 | self | Trusted Context7 docs for x402 SDK (`PaymentMiddleware` class) | x402 v2.2.0 has NO `PaymentMiddleware`. Build Flask middleware manually with `x402HTTPResourceServerSync` + `process_http_request()` |
| 2026-02-22 | self | Used `HTTPFacilitatorClientSync(url=...)` | Constructor takes `FacilitatorConfig` object, not `url` kwarg |
| 2026-02-22 | self | `FlaskHTTPAdapter` missing `get_url()` and `get_user_agent()` | `HTTPAdapter` protocol requires ALL methods — check with `inspect.getmembers()` before implementing |
| 2026-02-22 | self | Only caught `requests.RequestException` in rpc.py | `responses` library raises raw `ConnectionError` — catch `(requests.RequestException, ConnectionError)` |
| 2026-02-22 | self | Used `network="base-sepolia"` (v1 string) | x402 SDK v2 requires CAIP-2: `eip155:84532` (sepolia) or `eip155:8453` (mainnet) |
| 2026-02-22 | self | Only detected EIP-1967/1822 proxy slots | Real contracts (USDC) use older OpenZeppelin slots (`org.zeppelinos.proxy.implementation`). Include those too |
| 2026-02-22 | self | Test assertion said score 30 = MEDIUM | Score 30 is LOW (16-35 range). Know the scoring boundaries before writing assertions |
| 2026-02-23 | self | Uploaded updated app.py to `/root/risk-api/src/` but gunicorn loaded old code | Conway sandbox runs pip-installed package — gunicorn loads from `site-packages`, not source dir. Upload to BOTH paths or re-run `pip install -e .` |
| 2026-02-23 | self | Dexter facilitator down (522), x402 middleware failed silently at startup | Have fallback facilitator ready. OpenFacilitator (`pay.openfacilitator.io`) is a working free alternative for Base mainnet |

## User Preferences
- Prefers new private GitHub repos for new projects (not monorepo)
- Conventional commits: `feat|fix|chore|docs(scope): description`
- Taskmaster skill re-enabled (2026-02-22) — Stop hook restored in ~/.claude/settings.json

## Patterns That Work
- Build pipeline modules bottom-up with tests at each step (opcodes -> disassembler -> selectors -> patterns -> scoring -> engine -> app)
- `enable_x402=False` parameter on `create_app()` for testing route logic without payment gate
- Separate `client` and `client_with_x402` test fixtures for different test concerns
- `functools.lru_cache` on RPC calls with `clear_cache()` exposed for testing
- `python -c "help(SomeClass)"` to discover actual SDK APIs when docs are wrong
- Check facilitator `/supported` endpoint to see what scheme+network combos work

## Patterns That Don't Work
- Trusting Context7 MCP docs for x402 SDK — they describe APIs that don't exist in v2.2.0
- x402 `initialize()` in app startup without try/except — it hits the network and will crash if facilitator is down
- Running `git push` in background bash on Windows — tends to hang (credential helper issue). First push via `gh repo create --push` works, subsequent pushes may need manual terminal

## Domain Notes
- x402 SDK undeclared dependency: needs `httpx` at runtime, not listed in `x402[flask,evm]` extras
- x402.org facilitator supports: `eip155:84532` (v2 exact), `base-sepolia` (v1 exact)
- Coinbase mainnet facilitator: `https://api.cdp.coinbase.com/platform/v2/x402` — **requires CDP API key auth, returns 401 without it**
- **Dexter facilitator** (`https://x402.dexter.cash`): free, no auth, 20K settlements/day, Base mainnet — **DOWN 2026-02-23 (522 timeout)**
- **OpenFacilitator** (`https://pay.openfacilitator.io`): free, no auth, supports eip155:8453 v2 exact — **current production facilitator**
- x402 402 response: body is `{}`, payment details are in `Payment-Required` header (base64 JSON)
- USDC on Base: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` — OpenZeppelin proxy, scores 20/low
- WETH on Base: `0x4200000000000000000000000000000000000006` — clean, scores 0/safe
- `ExactEvmServerScheme` has a pyright type error (parameter name mismatch) — SDK bug, use `type: ignore[arg-type]`
- Conway sandbox pip has broken distro module — patch `encoding="ascii"` to `"utf-8"` in `pip/_vendor/distro/distro.py`
- Conway sandbox system python setuptools is read-only/corrupted — always use venv
- Conway sandbox 512MB is too small for x402 deps — use 1024MB minimum

## ERC-8004 Registration Notes (2026-02-23)
- Registry: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` on Base mainnet (ERC-1967 proxy)
- Function: `register(string agentURI)` — selector `0xf2c298be`
- Returns ERC-721 NFT (AGENT token) with unique agentId
- Cost: gas only (~$0.002 on Base), no protocol fee
- agentURI can be HTTPS URL, IPFS, or `data:application/json;base64,...`
- Post-register: `setAgentURI(agentId, newURI)` to update metadata
- 45,379+ agents registered across all chains, 19,069+ on Base
- No-code: 8004scan.io/create (requires wallet connect)
- `web3` and `eth_account` are available (transitive deps from x402) — can sign/send txs directly
- `web3.eth.contract().functions.register().build_transaction()` TxParams TypedDict is strict — use `type: ignore[arg-type]`

## x402.jobs Registration Notes (2026-02-23)
- API: `POST https://api.x402.jobs/api/v1/resources` with `x-api-key` header
- Required fields: `name`, `resource_url`. Optional: `description`, `category`, `tags`, `capabilities`, `server_name`
- Free tier during beta — sufficient for listing a resource
- Pricing auto-detected from x402 402 response
- Account required (email or X/Google OAuth) — no programmatic signup
- Rate limits: 100/min, 1000/hr per API key

## Graduation Queue
- **Context7 x402 distrust** — stable enough to graduate to CLAUDE.md: "Never trust Context7 for x402 SDK docs. Always verify imports against installed package."
- **CAIP-2 network format** — always use `eip155:CHAINID` not string names with x402 v2
- **Context7 doesn't have x402.jobs docs** — use direct scraping for x402.jobs API reference
