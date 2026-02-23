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

## User Preferences
- Prefers new private GitHub repos for new projects (not monorepo)
- Conventional commits: `feat|fix|chore|docs(scope): description`
- Taskmaster skill was disabled — user removed the Stop hook

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
- Coinbase mainnet facilitator: `https://api.cdp.coinbase.com/platform/v2/x402`
- USDC on Base: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` — OpenZeppelin proxy, scores 20/low
- WETH on Base: `0x4200000000000000000000000000000000000006` — clean, scores 0/safe
- `ExactEvmServerScheme` has a pyright type error (parameter name mismatch) — SDK bug, use `type: ignore[arg-type]`

## Graduation Queue
- **Context7 x402 distrust** — stable enough to graduate to CLAUDE.md: "Never trust Context7 for x402 SDK docs. Always verify imports against installed package."
- **CAIP-2 network format** — always use `eip155:CHAINID` not string names with x402 v2
