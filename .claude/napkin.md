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
| 2026-02-23 | self | Assumed x402 reads payment from `X-PAYMENT` header | SDK v2 reads from `PAYMENT-SIGNATURE` header via adapter's `get_header()`. The `payment_header` kwarg on `HTTPRequestContext` is ignored. Clients must send `PAYMENT-SIGNATURE`. |
| 2026-02-23 | self | Python `/tmp/` path in MINGW doesn't map to bash `/tmp/` | On MINGW/Windows, Python's tempfile uses `C:\Users\...\AppData\Local\Temp\`. Use project-relative paths instead. |
| 2026-02-23 | self | Conway file upload API: tried `{"files": [...]}` batch format | Conway expects one file per request: `{"path": "...", "content": "..."}` at top level. Loop over files. |
| 2026-02-23 | self | `eth_account.encode_typed_data()` — passed `primary_type` kwarg | This version doesn't accept `primary_type`. Use `full_message=` format with `primaryType` key in the dict instead. |
| 2026-02-24 | self | Restarted gunicorn with `export PRICE="$0.10"` — bash expanded `$0` to script name | Always use single quotes for dollar-sign values: `export PRICE='$0.10'`. Double quotes allow variable expansion. |
| 2026-02-24 | self | Tried to DELETE x402.jobs resource by slug with `x-api-key` header | x402.jobs DELETE only works by UUID: `DELETE /api/v1/resources/{uuid}` with `x-api-key`. Slug-based DELETE returns "Missing authorization header". |
| 2026-02-24 | self | Re-POSTed same resource URL to x402.jobs expecting upsert | x402.jobs POST creates a NEW resource with different slug (appends `-base`). Not idempotent — delete old resource first by UUID. |
| 2026-02-24 | self | Used `monkeypatch.delenv()` to isolate config tests from `.env` | `load_dotenv()` re-reads `.env` on every `load_config()` call, overriding monkeypatch. Must mock `load_dotenv` itself: `monkeypatch.setattr("risk_api.config.load_dotenv", lambda **kwargs: None)` |

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
- **Fake x402 gate for tests**: Patch `risk_api.app._setup_x402_middleware` with a lightweight `before_request` hook that returns 402 + proper `Payment-Required` headers (including Bazaar extensions). Avoids all x402 SDK imports. See `tests/conftest.py` for implementation.
- **`python -m pytest` instead of `pytest`** — pytest is installed but not on PATH in MINGW. `python -m pytest` always works.

## Patterns That Don't Work
- Trusting Context7 MCP docs for x402 SDK — they describe APIs that don't exist in v2.2.0
- x402 `initialize()` in app startup without try/except — it hits the network and will crash if facilitator is down
- Running `git push` in background bash on Windows — tends to hang (credential helper issue). First push via `gh repo create --push` works, subsequent pushes may need manual terminal
- **Mocking x402 SDK internals to speed up tests** — `patch('x402HTTPServerBase.initialize')`, `patch('HTTPFacilitatorClientSync.get_supported')`, `patch('httpx.Client')` all fail because the hang is at import time (`from x402.mechanisms.evm` pulls ~60 packages), not at method call time. Mock can't prevent an import-level hang.
- **Running `pip install` or `pyright` in background bash** — both trigger x402 EVM import chain which takes forever on Windows/MINGW (no `.pyc` write permission). Use `python -m pytest` directly (already installed), skip pyright locally.

## Domain Notes
- **x402 EVM import chain is massive**: `x402.mechanisms.evm` → `web3`, `eth_account`, `eth_abi`, `aiohttp`, `pydantic`, ~60 packages total. On Linux with `.pyc` caches: ~1s. On Windows/MINGW without writable `__pycache__`: hangs indefinitely (recompiles from source). This affects tests, pyright, and any local tool that imports x402 EVM code.
- **Fly.io 256MB is tight**: 1 gunicorn worker + x402 SDK import tree + caches. Reduced to 1 worker + smaller caches after OOM crash (2026-03-03). If OOM recurs: `fly scale memory 512 -a augurrisk`.
- x402 SDK undeclared dependency: needs `httpx` at runtime, not listed in `x402[flask,evm]` extras
- x402.org facilitator supports: `eip155:84532` (v2 exact), `base-sepolia` (v1 exact)
- Coinbase mainnet facilitator: `https://api.cdp.coinbase.com/platform/v2/x402` — **requires CDP API key auth, returns 401 without it**
- **Dexter facilitator** (`https://x402.dexter.cash`): free, no auth, 20K settlements/day, Base mainnet — **DOWN 2026-02-23 (522 timeout)**
- **OpenFacilitator** (`https://pay.openfacilitator.io`): free, no auth, supports eip155:8453 v2 exact — **current production facilitator**
- x402 402 response: body is `{}`, payment details are in `Payment-Required` header (base64 JSON)
- USDC on Base: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` — EIP-1967 proxy, impl `0x2ce6...d779` (23KB), scores 63/high (proxy+delegatecall+impl_delegatecall+impl_hidden_mint)
- WETH on Base: `0x4200000000000000000000000000000000000006` — scores 3/safe (deployer_reputation finding: precompile address has no Basescan deployer record)
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

## x402.jobs Platform Mechanics (2026-02-24)
- **Resources vs Jobs:** Resources = public directory listings (what agents discover). Jobs = internal workflow automations (chain triggers → resources → outputs). We care about Resources.
- **Custodial payments:** "Run" button payments are internal accounting, NOT on-chain USDC transfers. Earnings tracked separately from spending balance. Calling your own resource nets to zero.
- **On-chain settlement:** Does NOT happen through x402.jobs Run button. Direct API calls (not through x402.jobs) should go through facilitator settlement — this path is UNTESTED.
- **Health tracking:** x402.jobs tracks success/failure rates per resource, publicly visible. A 422 counts as a failure → "0% success / degraded" badge. Include a default working address in `resourceUrl` so the Run button works out of box.
- **API quirks:** POST (create) works with `x-api-key`. PUT/PATCH/DELETE by slug fail ("Missing authorization header"). DELETE by UUID works with `x-api-key`. Re-POST creates duplicate, not upsert.
- **Visibility factors:** Verified badge (claim server) + avatar + call count matter. Input Schema config enables proper Run button UX with input fields.
- **API key stored in:** `.env` (gitignored), read by `scripts/register_x402jobs.py` via `load_dotenv()`

## 8004scan UI Notes (2026-03-06)
- **Browser Wallet, not MetaMask** — clicking "MetaMask" in 8004scan connect modal triggers WalletConnect QR code flow. Use "Browser Wallet" to connect the extension directly.
- **Edit Agent wizard defaults to Data URI storage** — always switch to "IPFS URL" tab in Step 4 and paste the CID. Data URI mode encodes everything as base64 on-chain and loses IPFS pin.
- **Accessing Management tab = owner verified** — no separate "verify wallet" action on 8004scan. If you can see Management, you're authenticated as owner.
- **Oracle feedback score is automated** — the 1.5/5.0 (30/100) rating from `0xF653...` is the 8004scan reputation oracle, not a human. Flags `HIGH_RISK_SCORE` + `CONCENTRATED_FEEDBACK` are normal for new agents. Improves with real tx volume.
- **OASF skills field = category slugs** — e.g. `security_privacy`, NOT sub-skill names like `threat_detection`. Sub-skills exist under categories but are not valid at the service level. Schema: `https://schema.oasf.outshift.com/skill_categories`
- **OASF domains field = top-level slug** — `technology` not `technology/blockchain`. Slash format rejected.

## Graduation Queue
- **Context7 x402 distrust** — stable enough to graduate to CLAUDE.md: "Never trust Context7 for x402 SDK docs. Always verify imports against installed package."
- **CAIP-2 network format** — always use `eip155:CHAINID` not string names with x402 v2
- **Context7 doesn't have x402.jobs docs** — use direct scraping for x402.jobs API reference
- **Bash dollar-sign quoting** — when setting env vars with `$` in values (prices, paths), always use single quotes. Seen twice now (Conway restart + docs).
