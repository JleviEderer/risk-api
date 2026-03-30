# Codex Napkin Runbook

## Repo Workflow
1. **[2026-03-10] Public proof pages are registry-driven**
   Do instead: add new proof reports in `src/risk_api/proof_reports.py` and let `REPORT_PAGES` drive routing, sitemap inclusion, and request logging.
2. **[2026-03-10] Keep proof-report assets explicit**
   Do instead: use report-specific OG images for proof pages when promoting them; the generic `/avatar.png` reads like stock security art in social previews.
3. **[2026-03-16] Treat `pause()` as suspicious admin control, not silent allow**
   Do instead: keep `pause()` on the `suspicious_selector` path so transfer-freeze authority warns via `suspicious_selector_signal` without inventing a new detector or auto-block rule yet; keep admin trading-toggle aliases like `setTradingEnabled(bool)` and `enableTrading()` on that same warning path alongside `setSwapEnabled(bool)`, and keep selective fee-bypass aliases like `excludeFromFees(address,bool)` and `setIsExcludedFromFee(address,bool)` there alongside `excludeFromFee(address)`.
4. **[2026-03-16] Do not let orphan malicious selectors silently pass**
   Do instead: if a selector is in the malicious table but no concrete detector surfaces it, route it through the `suspicious_selector` warning path instead of returning clean `allow`.
5. **[2026-03-16] Run hidden discovery batches serially**
   Do instead: land, verify, and deploy each hidden holdout batch before starting the next one so each loop runs against the latest baseline and failures stay attributable; for this single-machine Fly app, keep `auto_stop_machines` off so production does not depend on the flaky auto-wake path.
6. **[2026-03-16] Keep fee/limit alias matching shared**
   Do instead: when you add fee-control selector aliases, reuse one label matcher across `detect_fee_manipulation()` and orphan-selector filtering so known limit controls warn at `15` instead of double-counting as `suspicious_selector`; keep transaction-limit aliases like `setMaxBuyAmount`, `setTxLimit`, and `setMaxTxnAmount` plus broader limit-control aliases like `setMaxWalletAmount`, `setMaxHoldAmount`, and `setMaxTransferAmount` in that same family.
7. **[2026-03-16] Delay full serial-batch autopilot until the fix pattern stabilizes**
   Do instead: keep the human in the loop between hidden batches while the research loop is still shaping itself; only automate commit/push/deploy-to-next-batch chaining after the allowed fix surfaces and stop conditions are explicit.
8. **[2026-03-17] `deployer_reputation` should use public Base Blockscout first**
   Do instead: use Blockscout creator lookup plus tx-history probes as the default deployer-reputation path, keep explorer failure distinct from true `NOT_FOUND`, keep throttling/soft-error handling, and treat `BLOCKSCOUT_API_KEY` as optional higher-limit support rather than making a paid Etherscan key the default dependency.
9. **[2026-03-29] Registration scripts are duplicated and easy to misuse**
   Do instead: when discovery wording or output shape changes, update not only `src/risk_api/app.py` plus `pin_metadata_ipfs.py` / `register_erc8004.py` / `register_x402jobs.py`, but also marketplace-specific scripts like `register_moltmart.py` and `register_work402.py`; keep argparse help paths safe and source-inspect operator scripts before assuming a flag is dry-run only.
10. **[2026-03-30] Treat wrapper families through executable bytecode only**
   Do instead: recognize 45-byte EIP-1167 runtimes as proxy shells, resolve their implementation from embedded bytecode before falling back to storage-slot reads, and strip Solidity CBOR metadata trailers before disassembly so wrapper families are judged on executable logic instead of `raw_delegatecall + tiny_bytecode` or other metadata-born false positives.

## Local Tooling
1. **[2026-03-12] On this 8 GB Intel iGPU laptop, QMD's safest high-quality mode is structured `lex+vec`**
   Do instead: treat `qmd search` as the fast exact path, `qmd vsearch` as the semantic path, and `qmd query "lex: ...\`nvec: ..."` as the default strong retrieval mode; reserve plain auto-expanded `qmd query "..."` for selective use and CPU fallback when the Vulkan path gets unstable.
2. **[2026-03-12] Build synthesis around QMD as a thin wrapper, not by modifying QMD itself**
   Do instead: implement a local `vault-synth` command that retrieves with QMD, fetches the top sources, sends them to an LLM for synthesis, prints answer plus sources by default, and saves to `Outputs/` only with an explicit flag.
3. **[2026-03-12] Windows wrappers can mangle multiline QMD `lex+vec` arguments**
   Do instead: if a local wrapper cannot pass a structured multiline `qmd query` argument cleanly, run `qmd search` and `qmd vsearch` separately and fuse the results instead of depending on newline transport through `qmd.cmd`.
4. **[2026-03-12] QMD can serve stale note content until the index is refreshed**
   Do instead: if retrieved note bodies disagree with the file on disk, run `qmd --index vault-core update` before trusting synthesis results; for `vault-synth`, refresh by default and only use `--no-refresh` when speed matters more than freshness.
5. **[2026-03-12] Saved synthesis notes can contaminate future retrieval**
   Do instead: exclude `vault-synth` generated notes from default retrieval so the tool does not cite or summarize its own prior answers as source material.

## Growth
1. **[2026-03-10] Use the live proof report as the first outreach artifact**
   Do instead: point early traffic to `https://augurrisk.com/reports/base-bluechip-bytecode-snapshot` before building more proof pages.
2. **[2026-03-19] Finish the turn from contract scoring to action-aware admission control**
   Do instead: keep Augur as `Base contract admission control for agents`, but treat the current `decision` / `recommended_policy` layer as v1; move next toward action-aware pre-transaction gates for `buy`, `approve`, `route`, `bridge`, or `pay` decisions, and do not respond by building a wallet product.
3. **[2026-03-19] Public copy should now lead with admission control, not scoring**
   Do instead: use `Deterministic Base contract admission control for agents` or `pre-transaction contract admission control for agents on Base` as the lead framing on current public surfaces; keep the 0-100 score as supporting output, not the headline.
4. **[2026-03-19] Explain the trigger moment in action terms**
   Do instead: pair the headline with a concrete sentence like `Decide whether a Base contract interaction should proceed before your agent buys, routes funds, approves, pays, or interacts`, and keep one compact use-case block on human-facing surfaces.
5. **[2026-03-19] Agent-native services only win if delegation beats self-computation**
   Do instead: when choosing roadmap work, prefer changes that make Augur more obviously worth calling than rebuilding in-agent: faster response, clearer policy output, stronger reliability, better edge-case coverage, and more machine-readable trust surfaces; publish concrete trust signals like uptime history, latency percentiles, and accuracy evidence, and return confidence metadata when uncertainty is real.
6. **[2026-03-20] Keep action-aware expansion narrow and recipient-aware**
   Do instead: if Augur moves beyond raw contract screening, extend it as destination-aware preflight for concrete actions like `deposit`, `approve`, `route`, or `pay`; validate claimed protocol + chain + recipient consistency, but do not drift into a generic phishing browser, wallet shield, or broad anti-scam suite.
7. **[2026-03-29] Keep the policy layer thin and explicit**
   Do instead: keep `allow` for clean `safe` outputs only, `warn` for residual non-blocking signals, `manual_review` for unresolved proxy/raw `DELEGATECALL`/`SELFDESTRUCT`/mint-capability-only cases, and `block` for honeypot or genuinely high-risk combinations rather than drifting into a complex custom policy engine.
8. **[2026-03-29] Managed upgradeable assets should escalate, not auto-block, on admin surfaces alone**
   Do instead: when a proxy-managed asset scores high because of upgradeability, mint/admin-control surface, delegatecall, and suspicious-selector signals, but not honeypot/selfdestruct/fee-manipulation-style hard stops, default to `manual_review` with an issuer-aware override summary instead of a flat `block`.
9. **[2026-03-16] Do not let raw `DELEGATECALL` hide inside the `safe` bucket**
   Do instead: if a contract has high-severity non-proxy `delegatecall`, force at least `manual_review` in policy even when the numeric score is only `15`.
10. **[2026-03-16] Use the new `auto/` harness for detector research, not free-form agent edits**
   Do instead: put reproducible cases in `auto/corpus/public_cases.json` or local `*.local.json` files, run `python auto/bench.py`, and only change implementation after the failure is locked into the corpus or pytest.
11. **[2026-03-16] Keep the tracked autoresearch corpus intentionally small**
   Do instead: use `auto/corpus/public_cases.json` for durable regressions, but keep the real search pressure in hidden `auto/corpus/*.local.json` holdouts and `auto/candidates/*.local.json` discoveries so the loop cannot simply memorize the public cases.

## Distribution
1. **[2026-03-10] Public entry pages are not the detector list**
   Do instead: label intent/SEO pages as entry pages or workflows, and keep full detector coverage described separately so agents do not confuse landing pages with product capability.
2. **[2026-03-10] Augur public surfaces stay agent-first**
   Do instead: prefer machine docs, direct call patterns, MCP setup, and x402/payment clarity over social-proof, testimonials, or human-first promo sections.
3. **[2026-03-10] Public MCP install copy should point at npm once published**
   Do instead: use `npx -y augurrisk-mcp` on `/mcp`, the homepage, `README.md`, and machine docs now that the package is live.
4. **[2026-03-10] MCP wrapper should stay in-repo unless it truly diverges**
   Do instead: keep `examples/javascript/augur-mcp` in this repo and treat `augurrisk-mcp` as the publish/distribution surface rather than splitting into a second codebase early.
5. **[2026-03-10] MCP startup should not require a wallet for read-only paths**
   Do instead: keep `examples/javascript/augur-mcp` usable for tool discovery and smoke startup without `CLIENT_PRIVATE_KEY`; require the key only when the paid analyze tool is invoked.
6. **[2026-03-10] Keep distribution posts in one outreach log**
   Do instead: record each forum/community post in `.codex/outreach.local.md` if it exists, otherwise keep `docs/outreach.md` current with date, surface, URL, status, and exact message.
7. **[2026-03-19] Outreach should sell Augur as admission control, not as a generic risk screen**
   Do instead: in posts, replies, and ecosystem submissions, lead with `contract admission control for agents` or `pre-transaction contract gate`, and use the proof page as supporting evidence rather than making `0-100 risk score` the headline.
8. **[2026-03-10] Treat OpenClaw as a secondary agent-builder channel**
   Do instead: test `r/OpenClaw` or OpenClaw Discord after Base/x402-first outreach, and avoid using the AI-only OpenClaw forum as the main posting surface.
9. **[2026-03-29] `x402.org/ecosystem` copy updates are manual PR work**
   Do instead: treat `x402.org/ecosystem` as curated content in `coinbase/x402`; script-driven runs update x402.jobs, MoltMart, and Work402, but stale ecosystem wording needs its own upstream PR.

## Research Hygiene
1. **[2026-03-10] Keep raw LLM research out of tracked docs**
   Do instead: store transcript dumps under `.codex/research.local/`; keep only synthesis memos and filled summary artifacts in `docs/`.
2. **[2026-03-10] LLM discoverability work needs clean-vs-contaminated separation**
   Do instead: distinguish pure blind runs from ambiguous or contaminated prompts before using headline counts as a benchmark.
3. **[2026-03-10] Augur has an entity-resolution problem, not just a discoverability problem**
   Do instead: make `Augur Risk`, `augurrisk.com`, `Base contract risk scoring API`, and `deterministic Base bytecode screening` co-occur across public docs and third-party mentions.
4. **[2026-03-10] LLM discoverability result currently shows a messaging problem first**
   Do instead: treat repeated `Base-only deterministic prefilter` framing and zero unprompted mentions as a category/distribution signal before deciding on a product pivot into simulation.

## Validation
1. **[2026-03-29] A healthy live app can still be metadata-stale**
   Do instead: before touching third-party listings, fetch `https://augurrisk.com/`, `openapi.json`, `skill.md`, `llms*.txt`, `/.well-known/agent-card.json`, `agent-metadata.json`, and `/.well-known/x402` and confirm the actual live wording matches the repo change you plan to propagate.
2. **[2026-03-26] Brief proxy-side drops do not always appear in the analytics DB**
   Do instead: for downtime forensics, query `/data/analytics.sqlite3` for durable request outcomes and pair it with Fly proxy logs so OOM-era `connection closed before message completed` events are not mistaken for zero-impact traffic.
3. **[2026-03-10] Treat Coinbase ecosystem and Bazaar as separate discovery surfaces**
   Do instead: verify `https://www.x402.org/ecosystem` and `https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources` independently; a live ecosystem listing does not prove CDP feed visibility.
4. **[2026-03-10] CDP feed absence after successful settlement is not automatically a repo bug**
   Do instead: after confirming live CDP settlement plus Bazaar extension metadata, treat continued absence from the public discovery feed as indexing lag, feed behavior, or support-escalation territory before rewriting metadata again.
5. **[2026-03-16] Treat recent `402` rows and `curl/...` agents as probe-sensitive clues**
   Do instead: for real production traffic forensics, pull `/data/analytics.sqlite3` from the Fly volume and query it directly; use `/dashboard`, `/stats`, and Fly logs as quick hints only, assume the newest rows may be your own probes, and treat `curl/...` as intent signals rather than proof of a human at the keyboard.
6. **[2026-03-16] Public examples must round-trip through the live serializer**
   Do instead: for OpenAPI examples, machine docs, and proof-report JSON, normalize fixtures through the same serializer the `/analyze` route uses so `implementation` omission and nested proxy payloads cannot drift.
7. **[2026-03-16] Keep private detector holdouts out of git**
   Do instead: store hidden autoresearch cases as `auto/corpus/*.local.json` or `auto/candidates/*.local.json`; load them locally with `python auto/bench.py` but do not promote them until they are ready to become public regressions.
8. **[2026-03-16] Proof reports can still drift semantically even when serializer shape matches**
   Do instead: keep `auto/bench.py` checking proof-report `decision` and `recommended_policy` against current `derive_policy()` semantics; a dated snapshot can keep old scores/findings, but stale policy recommendations should fail loudly unless you intentionally preserve historical policy and relax the check.
9. **[2026-03-16] Use `python auto/loop.py` for routine autoresearch runs**
   Do instead: treat `auto/loop.py` as the default human-facing runner; it writes `auto/runs/latest.json` and prints a compact grouped summary, while `auto/bench.py` remains the raw JSON/benchmark entrypoint.
10. **[2026-03-16] Do not collapse proxy `no_code` into transport failure**
   Do instead: if a proxy implementation address resolves but `eth_getCode` returns `0x`, emit `ProxyResolutionStatus.NO_CODE` plus `proxy_logic_no_code`; keep the action at `manual_review`, but preserve the distinction from RPC/lookup `fetch_failed`.
