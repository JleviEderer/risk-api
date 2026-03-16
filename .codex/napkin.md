# Codex Napkin Runbook

## Repo Workflow
1. **[2026-03-10] Public proof pages are registry-driven**
   Do instead: add new proof reports in `src/risk_api/proof_reports.py` and let `REPORT_PAGES` drive routing, sitemap inclusion, and request logging.
2. **[2026-03-10] Keep proof-report assets explicit**
   Do instead: use report-specific OG images for proof pages when promoting them; the generic `/avatar.png` reads like stock security art in social previews.

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
2. **[2026-03-11] Keep Augur's wedge narrow**
   Do instead: treat Augur as `Base contract admission control for agents`; improve decision-native outputs and clone/proxy interpretation before drifting into simulation or a broad execution-security platform.
3. **[2026-03-11] Keep public wedge wording plain**
   Do instead: use `Deterministic Base contract risk screening for agents` or similarly direct phrasing in public copy; keep `admission control` as internal strategy language if needed.
4. **[2026-03-11] Explain the trigger moment, not just the category**
   Do instead: pair the public headline with a concrete sentence like `Screen Base contracts before your agent buys, routes funds, approves, or interacts`, and keep one compact use-case block on human-facing surfaces.
5. **[2026-03-16] Keep the policy layer thin and explicit**
   Do instead: now that `/analyze` returns `decision` and `recommended_policy`, keep it as a default first-pass action layer (`allow`, `warn`, `manual_review`, `block`) with stable `reason_codes` instead of drifting into a complex custom policy engine.
6. **[2026-03-10] Keep proof-page claims narrower than the implementation**
   Do instead: frame the report as a dated snapshot, not a live rerun or a full product demo; use the payment explainer and dashboard as separate surfaces.
7. **[2026-03-10] Homepage polish should preserve the agent entry path**
   Do instead: keep the brand lockup, `skill.md` entry, and one obvious paid-call path visible above the fold even when tightening the visual hierarchy.
8. **[2026-03-10] Public entry pages are not the detector list**
   Do instead: label intent/SEO pages as entry pages or workflows, and keep full detector coverage described separately so agents do not confuse landing pages with product capability.
9. **[2026-03-10] Augur public surfaces stay agent-first**
   Do instead: prefer machine docs, direct call patterns, MCP setup, and x402/payment clarity over social-proof, testimonials, or human-first promo sections.
10. **[2026-03-10] Public MCP install copy should point at npm once published**
   Do instead: use `npx -y augurrisk-mcp` on `/mcp`, the homepage, `README.md`, and machine docs now that the package is live.
11. **[2026-03-10] MCP wrapper should stay in-repo unless it truly diverges**
   Do instead: keep `examples/javascript/augur-mcp` in this repo and treat `augurrisk-mcp` as the publish/distribution surface rather than splitting into a second codebase early.
12. **[2026-03-10] MCP startup should not require a wallet for read-only paths**
   Do instead: keep `examples/javascript/augur-mcp` usable for tool discovery and smoke startup without `CLIENT_PRIVATE_KEY`; require the key only when the paid analyze tool is invoked.
13. **[2026-03-10] Keep distribution posts in one outreach log**
   Do instead: record each forum/community post in `.codex/outreach.local.md` if it exists, otherwise keep `docs/outreach.md` current with date, surface, URL, status, and exact message.
14. **[2026-03-10] Treat OpenClaw as a secondary agent-builder channel**
   Do instead: test `r/OpenClaw` or OpenClaw Discord after Base/x402-first outreach, and avoid using the AI-only OpenClaw forum as the main posting surface.

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
1. **[2026-03-10] Public-surface cleanup should not remove discoverability docs**
   Do instead: keep `skill.md`, `llms.txt`, `llms-full.txt`, `openapi.json`, the proof page, and the MCP setup page live while avoiding accidental operator-only material in tracked docs.
2. **[2026-03-10] Treat Coinbase ecosystem and Bazaar as separate discovery surfaces**
   Do instead: verify `https://www.x402.org/ecosystem` and `https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources` independently; a live ecosystem listing does not prove CDP feed visibility.
3. **[2026-03-10] CDP feed absence after successful settlement is not automatically a repo bug**
   Do instead: after confirming live CDP settlement plus Bazaar extension metadata, treat continued absence from the public discovery feed as indexing lag, feed behavior, or support-escalation territory before rewriting metadata again.
