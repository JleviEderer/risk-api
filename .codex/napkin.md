# Codex Napkin Runbook

## Repo Workflow
1. **[2026-03-10] Public proof pages are registry-driven**
   Do instead: add new proof reports in `src/risk_api/proof_reports.py` and let `REPORT_PAGES` drive routing, sitemap inclusion, and request logging; reuse `/reports/base-weth-before-after` as the current Base WETH false-positive before/after proof artifact instead of recreating it elsewhere.
2. **[2026-03-10] Keep proof-report assets explicit**
   Do instead: use report-specific OG images for proof pages when promoting them; the generic `/avatar.png` reads like stock security art in social previews.
3. **[2026-03-16] Treat `pause()` as suspicious admin control, not silent allow**
   Do instead: keep `pause()` on the `suspicious_selector` path so transfer-freeze authority warns via `suspicious_selector_signal` without inventing a new detector or auto-block rule yet; keep admin trading-toggle aliases like `setTradingEnabled(bool)` and `enableTrading()` on that same warning path alongside `setSwapEnabled(bool)`, and keep selective fee-bypass aliases like `excludeFromFees(address,bool)` and `setIsExcludedFromFee(address,bool)` there alongside `excludeFromFee(address)`.
4. **[2026-03-16] Do not let orphan malicious selectors silently pass**
   Do instead: if a selector is in the malicious table but no concrete detector surfaces it, route it through the `suspicious_selector` warning path instead of returning clean `allow`.
5. **[2026-03-16] Run hidden discovery batches serially**
   Do instead: land, verify, and deploy each hidden holdout batch before starting the next one so each loop runs against the latest baseline and failures stay attributable; for this single-machine Fly app, keep `auto_stop_machines` off so production does not depend on the flaky auto-wake path, and after the selector/proxy-wrapper corpus goes green, move the next batch to under-covered families like `deployer_reputation`, proxy `no_code`, and `reentrancy` instead of spending another round on alias churn. When a hidden case depends on mocked RPC or explorer behavior, express it as an `analysis` case in `auto_bench` rather than flattening it into a lossy pure-policy surrogate.
6. **[2026-03-16] Keep fee/limit alias matching shared**
   Do instead: when you add fee-control selector aliases, reuse one label matcher across `detect_fee_manipulation()` and orphan-selector filtering so known limit controls warn at `15` instead of double-counting as `suspicious_selector`; keep transaction-limit aliases like `setMaxBuyAmount`, `setTxLimit`, and `setMaxTxnAmount` plus broader limit-control aliases like `setMaxWalletAmount`, `setMaxHoldAmount`, and `setMaxTransferAmount` in that same family.
7. **[2026-04-06] Deploy from a clean worktree when unrelated local changes are present**
   Do instead: if production needs only one narrow change and the main worktree is dirty with unrelated files, deploy from a detached worktree or equivalent clean checkout so you do not accidentally ship local research or scratch work.
8. **[2026-03-17] `deployer_reputation` should use public Base Blockscout first**
   Do instead: use Blockscout creator lookup plus tx-history probes as the default deployer-reputation path, keep explorer failure distinct from true `NOT_FOUND`, keep throttling/soft-error handling, and treat `BLOCKSCOUT_API_KEY` as optional higher-limit support rather than making a paid Etherscan key the default dependency. Hidden coverage should include partial explorer failure too, so a failed age probe or tx-count probe does not erase the other surviving deployer signal.
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
1. **[2026-04-06] Keep `approve` spender trust opt-in**
   Do instead: use `APPROVE_SPENDER_ALLOWLIST` as an optional narrow control for action-aware `approve`; keep default behavior unchanged when it is unset, let allowlisted spenders preserve clean `allow`, and escalate non-allowlisted spenders to `manual_review` instead of inventing broader protocol validation.
2. **[2026-04-06] Keep action-aware V1 narrow and additive**
   Do instead: for the first action-aware pass, support only `approve`, keep the contract engine and top-level `decision` unchanged, add `action_context` plus `action_evaluation` alongside the existing policy, and avoid claiming protocol-target validation or simulation until there is a real trusted source of truth.
3. **[2026-03-19] Finish the turn from contract scoring to action-aware admission control**
   Do instead: keep Augur as `Base contract admission control for agents`, but treat the current `decision` / `recommended_policy` layer as v1; move next toward action-aware pre-transaction gates for `buy`, `approve`, `route`, `bridge`, or `pay` decisions, and do not respond by building a wallet product.
4. **[2026-03-19] Public copy should now lead with admission control, not scoring**
   Do instead: use `Deterministic Base contract admission control for agents` or `pre-transaction contract admission control for agents on Base` as the lead framing on current public surfaces; keep the 0-100 score as supporting output, not the headline.
5. **[2026-03-19] Explain the trigger moment in action terms**
   Do instead: pair the headline with a concrete sentence like `Decide whether a Base contract interaction should proceed before your agent buys, routes funds, approves, pays, or interacts`, and keep one compact use-case block on human-facing surfaces.
6. **[2026-03-19] Agent-native services only win if delegation beats self-computation**
   Do instead: when choosing roadmap work, prefer changes that make Augur more obviously worth calling than rebuilding in-agent: faster response, clearer policy output, stronger reliability, better edge-case coverage, and more machine-readable trust surfaces; publish concrete trust signals like uptime history, latency percentiles, and accuracy evidence, and return confidence metadata when uncertainty is real.
7. **[2026-03-20] Keep action-aware expansion narrow and recipient-aware**
   Do instead: if Augur moves beyond raw contract screening, extend it as destination-aware preflight for concrete actions like `deposit`, `approve`, `route`, or `pay`; validate claimed protocol + chain + recipient consistency, but do not drift into a generic phishing browser, wallet shield, or broad anti-scam suite.
8. **[2026-03-29] Keep the policy layer thin and explicit**
   Do instead: keep `allow` for clean `safe` outputs only, `warn` for residual non-blocking signals, `manual_review` for unresolved proxy/raw `DELEGATECALL`/`SELFDESTRUCT`/mint-capability-only cases, and `block` for honeypot or genuinely high-risk combinations rather than drifting into a complex custom policy engine.
9. **[2026-03-29] Managed upgradeable assets should escalate, not auto-block, on admin surfaces alone**
   Do instead: when a proxy-managed asset scores high because of upgradeability, mint/admin-control surface, delegatecall, and suspicious-selector signals, but not honeypot/selfdestruct/fee-manipulation-style hard stops, default to `manual_review` with an issuer-aware override summary instead of a flat `block`.
10. **[2026-03-16] Do not let raw `DELEGATECALL` hide inside the `safe` bucket**
   Do instead: if a contract has high-severity non-proxy `delegatecall`, force at least `manual_review` in policy even when the numeric score is only `15`.

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
10. **[2026-04-06] Ship new action-aware messaging on first-party docs before registry churn**
   Do instead: when product positioning stays the same but you need to make a new action-aware capability legible, update the homepage plus `skill.md` / `llms.txt` / `llms-full.txt` first with one exact request and response example; only rerun registry and marketplace updates if the core public positioning actually changes.

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
1. **[2026-06-04] Keep public `/stats` bounded over durable SQLite**
   Do instead: aggregate dashboard totals with SQLite queries and read `raw_json` only for recent rows; store `traffic_class` as a column and keep SQL fallback classification for older rows so a grown `/data/analytics.sqlite3` cannot make `/stats` time out and break `/dashboard`; do not bulk-backfill old analytics rows inside a public request on the 512 MB Fly VM.
2. **[2026-04-09] Separate evaluator traffic from real demand in Fly analytics**
   Do instead: use `/dashboard` Traffic Quality Classes plus the request `traffic_class` field and `/stats.traffic_classes` first; treat `/.well-known/x402`, `/.well-known/agent-card.json`, `openapi.json`, `llms*.txt`, health checks, and repeated Base WETH `402` or paid probes as machine-evaluator traffic unless a real integration trail proves otherwise; judge traction from repeated non-smoke paid calls and successful first-call conversion, not raw high-intent counts.
3. **[2026-04-06] Observe narrow action-aware behavior before widening the API**
   Do instead: log `approve` spender trust and action-level decision first, ship that narrow instrumentation with the current allowlist refinement, and only add extra public response fields if live usage shows the reason codes are not enough.
4. **[2026-04-06] After an action-aware deploy, verify `/stats` as well as the route**
   Do instead: after a paid action-aware smoke, check the durable recent entry in `/stats` for `action`, `action_spender_trust`, and `action_decision` so you confirm both the public response and the production observability path before deciding on further API changes.
5. **[2026-04-03] Do not let `/analyze` hooks override Flask's method contract**
   Do instead: keep address validation and x402 gating limited to the real `/analyze` request methods (`GET`, `POST`, `HEAD`) so `OPTIONS` stays ungated and unsupported methods return Flask's native `405` instead of misleading `422`/`402` responses.
6. **[2026-03-29] A healthy live app can still be metadata-stale**
   Do instead: before touching third-party listings, fetch `https://augurrisk.com/`, `openapi.json`, `skill.md`, `llms*.txt`, `/.well-known/agent-card.json`, `agent-metadata.json`, and `/.well-known/x402` and confirm the actual live wording matches the repo change you plan to propagate.
7. **[2026-03-30] A Fly deploy timeout can still leave the new image in place**
   Do instead: if `flyctl deploy --remote-only` times out during health polling, immediately check `flyctl status --app augurrisk` plus the live public routes; if the machine image/version advanced and the public app is healthy, treat the deploy as landed even if Fly's polling call failed.
8. **[2026-07-06] A healthy Augur app can still be dead-linked in CDP/Bazaar**
   Do instead: check CDP/Bazaar discovery directly with `scripts/check_cdp_discovery.py`, `/discovery/merchant?payTo=...`, and `/discovery/search?urlSubstring=...` before treating discovery as fixed; live `augurrisk.com` passed CDP validate and a fresh paid settlement succeeded, but CDP still only surfaced `https://risk-api.life.conway.tech/analyze` after the 2026-07-07 recheck, so use `docs/CDP_BAZAAR_ESCALATION_2026-07-06.md` and send it through CDP support or the CDP/x402 Discord rather than changing app code.
9. **[2026-03-16] Treat recent `402` rows and `curl/...` agents as probe-sensitive clues**
   Do instead: for real production traffic forensics, pull `/data/analytics.sqlite3` from the Fly volume and query it directly; use `/dashboard`, `/stats`, and Fly logs as quick hints only, assume the newest rows may be your own probes, and treat `curl/...` as intent signals rather than proof of a human at the keyboard. Keep `/stats` fail-soft on malformed JSONL rows rather than letting one bad log line break the public ops view.
10. **[2026-03-16] Public examples must round-trip through the live serializer**
   Do instead: for OpenAPI examples, machine docs, and proof-report JSON, normalize fixtures through the same serializer the `/analyze` route uses so `implementation` omission and nested proxy payloads cannot drift.
