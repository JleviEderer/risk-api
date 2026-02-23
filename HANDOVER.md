# Handover — risk-api

**Session date:** 2026-02-22
**Repo:** https://github.com/JleviEderer/risk-api (private)
**Commit:** `456b300` on `master` — initial implementation, pushed to GitHub

---

## What We Built

A complete smart contract risk scoring API from scratch. No code existed before this session — everything was greenfield.

**Product:** Deterministic EVM bytecode risk analysis sold agent-to-agent via x402 at $0.01/call on Base. Pure pattern matching, no LLM inference per request.

**Architecture:** `opcodes → disassembler → selectors/patterns → scoring → engine → Flask app + x402 middleware`

### Files Created (29 files, 1,965 lines)

```
risk-api/
├── pyproject.toml                         # Package config, deps, pytest config
├── .env.example                           # Required: WALLET_ADDRESS
├── .gitignore
├── CLAUDE.md                              # Project-specific rules & gotchas
├── src/risk_api/
│   ├── __init__.py
│   ├── app.py                             # Flask app factory + x402 middleware
│   ├── config.py                          # Env loading (WALLET_ADDRESS required)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── opcodes.py                     # 149 EVM opcodes: int → (name, operand_size)
│   │   ├── disassembler.py                # Bytecode hex → list[Instruction]
│   │   ├── selectors.py                   # Function selector extraction + malicious DB
│   │   ├── patterns.py                    # 7 detectors (selfdestruct, delegatecall, etc.)
│   │   ├── scoring.py                     # Weighted 0-100 composite scoring
│   │   └── engine.py                      # Orchestrator: fetch → disassemble → detect → score
│   └── chain/
│       ├── __init__.py
│       └── rpc.py                         # Base RPC client (eth_getCode via requests)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                        # Fixtures: test_config, app, client, client_with_x402
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── bytecodes.py                   # Hardcoded test bytecodes (clean, proxy, honeypot, etc.)
│   ├── test_opcodes.py                    # 6 tests
│   ├── test_disassembler.py               # 7 tests
│   ├── test_selectors.py                  # 6 tests
│   ├── test_patterns.py                   # 16 tests
│   ├── test_scoring.py                    # 8 tests
│   ├── test_rpc.py                        # 6 tests
│   ├── test_engine.py                     # 5 tests
│   └── test_app.py                        # 10 tests (incl. x402 402 verification)
└── scripts/
    └── fetch_test_bytecodes.py            # One-time: fetch real bytecodes from Base
```

### Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/ -v --cov` | 64 passed, 91% coverage |
| `pyright src/risk_api/` | 0 errors, 0 warnings |
| `/health` endpoint | 200 OK |
| `/analyze` without payment | 402 Payment Required |
| USDC (real contract) | Score 20, level "low" (proxy + delegatecall INFO) |
| WETH (real contract) | Score 0, level "safe" |

---

## What Worked and What Didn't

### Worked smoothly
- The entire analysis pipeline (opcodes → disassembler → selectors → patterns → scoring → engine) built cleanly with tests passing on first or second try
- `responses` library for mocking HTTP in rpc/engine tests
- Scoring formula and category caps worked as designed

### Problems encountered and fixed

1. **`setuptools.backends._legacy` doesn't exist** — pyproject.toml had wrong build-backend. Fixed to `setuptools.build_meta`.

2. **`responses` library raises raw `ConnectionError`** — not wrapped in `requests.RequestException`. Fixed by catching `(requests.RequestException, ConnectionError)` in `rpc.py`.

3. **Context7 docs were WRONG about x402 SDK** — Claimed `from x402.flask.middleware import PaymentMiddleware` exists. It does NOT in v2.2.0. The actual API requires manually building Flask middleware using:
   - `x402HTTPResourceServerSync` + `process_http_request()` for the before_request gate
   - `FlaskHTTPAdapter` class implementing the `HTTPAdapter` protocol
   - `process_settlement()` in after_request for payment settlement

4. **`HTTPFacilitatorClientSync` constructor** — Context7 showed `url=` kwarg. Real API requires `FacilitatorConfig(url=...)` object.

5. **`FlaskHTTPAdapter` missing methods** — `HTTPAdapter` protocol requires `get_url()` and `get_user_agent()` which weren't in the initial implementation. Added them.

6. **x402 SDK needs `httpx` at runtime** — Undeclared transitive dependency. `x402[flask,evm]` installs Flask and web3 but doesn't declare httpx. Had to add it to pyproject.toml.

7. **Network string format** — `base-sepolia` is v1 format. SDK v2.2.0 requires CAIP-2: `eip155:84532`. The x402.org facilitator supports both but only v2 on the CAIP-2 identifier.

8. **USDC proxy detection failed initially** — USDC uses older OpenZeppelin proxy slots (`org.zeppelinos.proxy.implementation`), not EIP-1967. Added `OZ_IMPL_SLOT` and `OZ_ADMIN_SLOT` to `PROXY_SLOTS` set.

9. **Tests broke when x402 middleware started working** — Once httpx was installed and CAIP-2 network was correct, the middleware activated and all `/analyze` tests got 402. Fixed by adding `enable_x402=False` parameter to `create_app()` and using separate `client` vs `client_with_x402` fixtures.

---

## Key Decisions

1. **No web3.py** — Too heavy. Raw JSON-RPC via `requests` for `eth_getCode` only.
2. **All selector hashes hardcoded** — Avoids keccak256 dependency. Keccak-256 != SHA3-256, so stdlib won't work.
3. **`enable_x402` flag on `create_app()`** — Tests use `enable_x402=False` to test route logic without payment gate. Separate `client_with_x402` fixture for 402 behavior tests.
4. **Proxy detection includes OpenZeppelin legacy slots** — Not just EIP-1967/1822. Real-world contracts (USDC) use older patterns.
5. **x402 middleware is hand-built** — SDK provides building blocks, not a drop-in Flask middleware. Our `FlaskHTTPAdapter` + `before_request`/`after_request` hooks are the integration layer.
6. **`functools.lru_cache` on `get_code()`** — Avoids redundant RPC calls. `clear_cache()` exposed for testing.
7. **One `type: ignore` in app.py** — x402 SDK has a parameter name mismatch (`extension_keys` vs `extensions`) in `ExactEvmServerScheme`. Pyright flags it but runtime works fine. SDK bug, not ours.

---

## Lessons Learned / Gotchas

- **Never trust Context7 docs for x402** — The documented `PaymentMiddleware` class does not exist in v2.2.0. Always verify imports against the actual installed package.
- **x402 `initialize()` hits the network** — It calls the facilitator's `/supported` endpoint. Wrap in try/except for graceful degradation when facilitator is unreachable.
- **The `responses` library and `ConnectionError`** — When you set `body=ConnectionError(...)`, it raises the raw exception, not a `requests.RequestException`. Catch both.
- **Taskmaster skill** was disabled this session (removed Stop hook from `~/.claude/settings.json`). The hook scripts still exist at `~/.claude/hooks/` and `~/.claude/skills/taskmaster/`.

---

## Next Steps

1. **Deploy to VPS** — The app runs locally. Need to deploy to a $5-8/month VPS with `WALLET_ADDRESS` and `NETWORK=eip155:8453` (mainnet) set.
2. **Switch to mainnet** — Change `NETWORK` to `eip155:8453` and `FACILITATOR_URL` to `https://api.cdp.coinbase.com/platform/v2/x402` (Coinbase hosted, free tier 1K tx/month).
3. **Register on ERC-8004** — Permissionless on Base mainnet at `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`. Register the API endpoint + wallet.
4. **List on x402.jobs** — Public discovery for agent-to-agent commerce.
5. **Expand detectors** — Current 7 detectors are a solid foundation. Could add: storage collision detection, access control analysis, token standard compliance checks.
6. **Integration tests with real RPC** — `tests/fixtures/bytecodes.py` has samples but no `@pytest.mark.integration` tests that hit real Base mainnet yet. The `scripts/fetch_test_bytecodes.py` can populate real bytecodes.
7. **Add Basescan deployer lookup** — `rpc.py` has a placeholder concept but deployer analysis isn't implemented yet.

---

## Commands

```bash
cd C:/Users/justi/dev/web4/risk-api

# Install
pip install -e ".[dev]"

# Test
pytest tests/ -v --cov=src/risk_api

# Type check
pyright src/risk_api/

# Run locally
WALLET_ADDRESS=0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891 flask --app risk_api.app:create_app run

# Verify endpoints
curl http://localhost:5000/health          # → 200 {"status": "ok"}
curl http://localhost:5000/analyze?address=0x...  # → 402 (no payment)
```
