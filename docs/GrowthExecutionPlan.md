# Augur - Growth Execution Plan

> Last updated: 2026-03-26

This document is the operating backlog for traffic, conversion, and revenue growth.

North star:
- Increase organic paid calls to `/analyze`

Companion strategy memo:
- See `docs/PRODUCT_DIRECTION_UPDATE.md` for the current product-direction view: Augur as pre-transaction contract admission control for agents on Base.
- Treat `docs/PRODUCT_WEDGE_MEMO.md` as background context, not the newest call.

Leading indicators:
- paid conversion rate from unique visitors
- number of real paid calls per week
- number of valid unpaid `402` attempts
- number of invalid or no-bytecode requests
- referrals from registries, directories, and docs

---

## Funnel Diagnosis

Current pattern:
- 200+ visitors
- 0 organic paying calls

Interpretation:
- discovery exists
- first-use conversion is weak
- buyer trust and integration clarity are the primary bottlenecks

---

## Workstreams

### 1. Product Trust and Correctness

Goal:
- make the first product impression technically credible

Now:
- Hard-error when an address has no bytecode on Base
- Replace all confusing example addresses with canonical Base examples
- Audit the live site, OpenAPI examples, Bazaar examples, and `llms.txt` for Base/mainnet confusion

Success criteria:
- wallet or wrong-address inputs do not return `safe`
- all public examples use the same Base contract set
- first-time testers cannot accidentally get a misleading result

### 2. Canonical Domain and Registry Hygiene

Goal:
- concentrate trust and discoverability on `augurrisk.com`

Now:
- Audit x402.jobs, x402list.fun, ERC-8004 metadata, Bazaar entries, and any public references
- Keep all editable listings and metadata on `augurrisk.com`
- If old domains are still live or indexable, ensure they redirect to the canonical host

Success criteria:
- all important registries point to `augurrisk.com`
- search and directory traffic do not split across old and new domains

### 3. Conversion and Onboarding

Goal:
- make the payment path easy to understand and verify

Now:
- Promote the existing x402 client flow into first-class docs
- Add a polished Python example and a JavaScript example
- Add a short "how x402 payment works for Augur" page linked from the homepage

Next:
- Consider a static preview page or sample report page
- Consider a free demo endpoint only if conversion remains blocked after the above

Success criteria:
- a new developer can complete a paid call in under 10 minutes
- unpaid `402` attempts increase before paid conversion improves

### 4. Distribution and Packaging

Goal:
- show up in the tools and surfaces agent developers already use

Now:
- Submit Augur to `x402.org/ecosystem`
- Build an MCP wrapper or MCP-compatible packaging surface

Next:
- Keep registry and directory hygiene as maintenance, not the whole distribution strategy
- Add AI-answer visibility work as a separate track from registries:
  - monitor whether Augur is cited or recommended in ChatGPT, Perplexity, Claude, and Gemini answers
  - improve citation-friendly proof, examples, and third-party mentions
- Treat operator ecosystems as their own track:
  - test OpenClaw and similar skill or workflow ecosystems as installable operator-channel distribution
  - keep that separate from public registry work
- Add framework-specific wrappers only if demand appears
- LangChain tool definition
- OpenAI function schema
- Claude tool schema

Success criteria:
- Augur appears in higher-signal ecosystem surfaces
- developers can integrate Augur through tool-first workflows, not just raw HTTP
- discoverability work is split cleanly across:
  - registries and directories
  - AI-answer visibility
  - operator ecosystems and installable workflows

### 5. Buyer-Intent Surface Area

Goal:
- expand search and LLM discoverability without splitting the paid API

Now:
- Create intent pages like:
  - `/honeypot-detection-api`
  - `/proxy-risk-api`
  - `/deployer-reputation-api`
  - `/compare/goplus-vs-augur`
  - `/use-cases/agent-trading-guardrails`

Next:
- Publish public report pages for notable Base contracts
- Publish recurring data pages such as newly scored contracts or high-risk contract snapshots

Success criteria:
- non-directory traffic grows
- Augur gets cited for specific contract-security intents, not just generic x402 searches

### 6. Proof and Community Distribution

Goal:
- prove usefulness in public where the target audience already spends time

Now:
- Publish one high-quality score report on known Base contracts
- Share it in Base and x402 communities

Next:
- Turn report findings into short X threads and developer-oriented posts
- Test whether AI-answer visibility tools or GEO-style workflows help Augur appear in answer engines
- Reuse proof and machine-readable docs anywhere third-party communities, operator ecosystems, or answer-engine workflows pull source material from
- Repeat only if posts generate qualified traffic

Success criteria:
- at least one external community post drives traffic from relevant developers
- proof content gets reused in landing pages and registry descriptions
- answer-engine visibility improves without confusing that work with registry cleanup

### 7. Measurement

Goal:
- know where the funnel is breaking before adding more work

Now:
- Split analytics into:
  - landing page views
  - valid unpaid `402` attempts
  - invalid address requests
  - no-bytecode requests
  - paid requests

Next:
- Track request source where possible

Success criteria:
- we can answer "where are visitors coming from?" and "where do they drop?" with data

---

## Status

As of 2026-03-26:

- the early trust, canonical-domain, packaging, and proof baseline is mostly complete
- the main unfinished growth items are still targeted distribution plus better source attribution
- the next growth work should be treated as three separate channels:
  - registry and directory maintenance
  - AI-answer visibility and citation work
  - operator ecosystems such as OpenClaw and installable workflow surfaces

---

## Baseline Checklist

Use this as the historical baseline for what has already been handled versus what is still open.

### P0 - Trust and Correctness

- [x] `G-001` Hard-error no-bytecode inputs
  Output: `/analyze` returns an explicit error when the address has no contract bytecode on Base.
  Why now: prevents wallet or wrong-address inputs from returning a misleading `safe` result.
  Depends on: none.
  Done means: route behavior, docs, and tests all reflect the new error case.

- [x] `G-002` Standardize all public example addresses
  Output: one canonical Base example set used across landing page, OpenAPI, Bazaar examples, `llms.txt`, scripts, and docs.
  Why now: removes Base versus mainnet confusion from the first impression.
  Depends on: none.
  Done means: no public examples use mismatched or ambiguous addresses.

- [x] `G-003` Audit public output and wording for trust leaks
  Output: pass through homepage, docs, examples, and machine-readable metadata for wording that could confuse buyers.
  Why now: trust breaks before payment if examples, labels, or chain references feel inconsistent.
  Depends on: `G-002`.
  Done means: one documented canonical message for what Augur does, on which chain, and for whom.

### P0 - Canonical Surface

- [x] `G-004` Audit all registry and directory listings
  Output: current-state table for x402.jobs, x402list.fun, ERC-8004, Bazaar, x402 ecosystem, and any other meaningful directory.
  Why now: you need a verified source of truth before editing registry metadata.
  Depends on: none.
  Done means: every listing is marked as correct, stale, missing, or blocked.

- [x] `G-005` Update stale Conway-domain references
  Output: all editable listings and metadata point to `augurrisk.com`.
  Why now: duplicate hosts split trust and discoverability.
  Depends on: `G-004`.
  Done means: no important listing intentionally points at the Conway domain.

- [x] `G-006` Enforce canonical host behavior
  Output: if old domains are still live or indexable, they redirect or otherwise stop competing with the canonical domain in public discovery.
  Why now: registry cleanup is weaker if an old host still looks active and indexable.
  Depends on: `G-004`.
  Done means: canonical host policy is documented and verified, or the audit confirms no redirect work is needed.

### P0 - Measurement Baseline

- [x] `G-016` Instrument the funnel stages
  Output: analytics distinguish landing views, valid unpaid `402` attempts, invalid addresses, no-bytecode requests, and paid requests.
  Why now: future prioritization should be based on actual drop-off, not guesses.
  Depends on: `G-001`.
  Done means: the dashboard or stats surface can answer where the funnel breaks.

### P1 - Distribution and Packaging

- [x] `G-007` Submit Augur to `x402.org/ecosystem`
  Output: Augur appears on the official ecosystem surface, not just secondary directories.
  Why now: higher-signal placement than another directory-clone optimization.
  Depends on: `G-004`.
  Done means: submission is live or blocked with a documented follow-up.
  Status: upstream `coinbase/x402` PR #1515 was approved and merged into `main` on 2026-03-09 after the verified-signature requirement was fixed. Remaining follow-up is live listing verification on `https://www.x402.org/ecosystem` after Coinbase's site deploy/index refresh.

- [x] `G-008` Define the MCP packaging approach
  Output: choose the minimum viable MCP surface: wrapper, server, or adapter.
  Why now: this is the cleanest path into the tools real agent builders already use.
  Depends on: `G-001`, `G-002`.
  Done means: one implementation path is selected with file targets and expected UX.
  Status: documented in `docs/MCP_PACKAGING_PLAN.md`. Chosen path is a local Node stdio MCP server that acts as an x402-paying client bridge to the canonical Augur HTTP API.

- [x] `G-009` Ship MCP-compatible integration
  Output: working MCP distribution artifact plus usage docs.
  Why now: packaging matters more than another endpoint right now.
  Depends on: `G-008`.
  Done means: a developer can add Augur through an MCP-style workflow without reading the whole codebase.
  Status: `examples/javascript/augur-mcp` now provides a working stdio MCP server, README wiring instructions, and smoke tests including one paid MCP tool invocation against live `https://augurrisk.com/analyze`.

### P1 - Conversion and Onboarding

- [x] `G-010` Promote the existing Python payment flow into first-class docs
  Output: visible, polished docs based on the existing real-client flow.
  Why now: the integration barrier is likely larger than the pricing barrier.
  Depends on: `G-001`, `G-002`.
  Done means: the fastest path from homepage to first successful paid call is documented.
  Status: README now links a first-class Python paid-call path and `docs/PYTHON_PAYMENT_QUICKSTART.md` documents the successful flow around `scripts/test_x402_client.py`.

- [x] `G-011` Add a JavaScript x402 client example
  Output: one browser or Node-oriented payment example that mirrors the Python path.
  Why now: not every buyer will test from Python.
  Depends on: `G-010`.
  Done means: both Python and JavaScript examples are available and tested enough to trust.
  Status: `examples/javascript/augur-paid-call` now provides a Node example using `@x402/fetch` and `@x402/evm`, with a dry-run mode and README entry.

- [x] `G-012` Publish a short "How Augur payment works" page
  Output: concise explanation of `402 -> sign payment -> retry with PAYMENT-SIGNATURE -> receive JSON`.
  Why now: buyers should not need to reverse-engineer the payment flow from scripts.
  Depends on: `G-010`.
  Done means: homepage and docs link directly to this explanation.
  Status: live `/how-payment-works` page is published in the app, linked from the homepage, and referenced from the README quickstart section.

### P2 - Intent Surface and Proof

- [x] `G-013` Ship the first buyer-intent pages
  Output: a small set of static pages aimed at specific contract-security intents.
  Why now: multiplies SEO and LLM surface without splitting the paid API.
  Depends on: `G-003`.
  Done means: at least three intent pages are live with clear internal links to Augur.
  Status: live public pages now exist at `/honeypot-detection-api`, `/proxy-risk-api`, and `/deployer-reputation-api`, each linking back to the canonical paid `/analyze` endpoint and the core discovery docs. The landing page and sitemap include all three.

- [x] `G-014` Publish one proof-of-work report
  Output: one high-quality report on notable Base contracts using Augur's scoring output.
  Why now: proof beats claims for early trust building.
  Depends on: `G-001`, `G-002`.
  Done means: one report is live and reusable in outreach.
  Status: live report page now exists at `/reports/base-bluechip-bytecode-snapshot`, publishing a 2026-03-09 Augur snapshot on Base WETH, USDC, and cbBTC with exact point-in-time score output plus interpretation about what bytecode-first screening does and does not prove.
  Note: the scoped post-`G-014` execution-based honeypot expansion is documented separately in `docs/HONEYPOT_EXECUTION_PHASE2.md`; do not treat that design as a prerequisite for publishing the first proof-of-work report.

- [ ] `G-015` Do one targeted distribution push
  Output: one post in a relevant Base or x402 community plus one supporting social or developer post.
  Why now: this validates whether proof content brings qualified traffic.
  Depends on: `G-014`.
  Done means: referral traffic from the post can be observed.

### P2 - Measurement

- [ ] `G-017` Add referral/source tracking where feasible
  Output: basic source attribution for registries, directories, docs, and community posts.
  Why now: discoverability work cannot be evaluated without some source visibility.
  Depends on: `G-016`.
  Done means: major acquisition surfaces can be compared with simple data.
  Status: app-level request logging now exists in `src/risk_api/app.py` for the landing page, payment page, buyer-intent pages, key machine-readable discovery docs, and `/analyze`, including `host`, `referer`, `request_id`, and stage summaries in `/stats`. Production is now using a Fly-mounted SQLite-backed event store via `ANALYTICS_DB_PATH`, so `/stats` and `/dashboard` survive restarts on the active machine volume. Edge-layer visibility for old-domain `403` traffic and any future multi-machine analytics design are still not complete.

### P2 - New Distribution Tracks

- [ ] `G-018` Add AI-answer visibility as a measured workstream
  Output: one lightweight process for checking whether Augur appears in answer-engine responses and which proof or documentation surfaces get cited.
  Why now: Augur has a real discoverability problem that is not the same as missing directory listings.
  Depends on: `G-014`, `G-017`.
  Done means: AI-answer visibility is tracked separately from registry status and community-post traffic.

- [ ] `G-019` Test one operator-ecosystem distribution path
  Output: one deliberate experiment in an operator ecosystem such as OpenClaw or a nearby installable-skill workflow surface.
  Why now: installable workflows are a different acquisition channel from public directories and may fit agent operators better.
  Depends on: `G-009`, `G-015`.
  Done means: one operator-channel experiment is executed and judged on qualified traffic or integration pull, not vanity impressions.

---

## Sequencing

### Now

1. `G-015`
2. `G-017`
3. `G-018`
4. `G-019`

### Next

1. tighten any remaining duplicated discovery metadata if public wording changes again
2. expand proof and machine-readable surfaces only if those channels show traction
3. add framework-specific wrappers only if there is real integration pull

### Later

1. Framework-specific tool wrappers
2. Demo endpoint
3. Endpoint splitting
4. Second domain strategy
5. Alternate payment rails

---

## Operating Rules

1. Fix trust leaks before adding surface area.
2. Prefer one strong canonical domain over many weak duplicates.
3. Multiply discoverability with content and packaging before multiplying paid endpoints.
4. Treat any vanity-metric tactic as a credibility risk.
5. Do not promote major new channels until measurement can show whether they work.
