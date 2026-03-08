# x402 Ecosystem Submission

Submission-ready packet for adding Augur to the official `x402.org/ecosystem` surface.

## Current Status

- Verified on 2026-03-08: `https://www.x402.org/ecosystem` does not list `Augur`, `augurrisk`, or `risk-api`.
- Upstream submission path is a GitHub pull request to `coinbase/x402`.
- This repo now contains the exact metadata payload needed for that PR.

## Upstream Instructions

The `coinbase/x402` demo-site README currently says ecosystem additions should:

1. Fork `coinbase/x402`
2. Create `typescript/site/app/ecosystem/partners-data/[your-project-slug]`
3. Add a logo file under `typescript/site/public/logos/`
4. Add `metadata.json`
5. Open a pull request

For Augur, use slug `augur`.

## Files To Add Upstream

- `typescript/site/app/ecosystem/partners-data/augur/metadata.json`
  Source: `docs/submissions/x402-ecosystem/metadata.json`
- `typescript/site/public/logos/augur.png`
  Source image in this repo: `x402JobsAvatar.png`

## Proposed Metadata

```json
{
  "name": "Augur",
  "description": "Base mainnet smart contract bytecode risk scoring API for agents and the developers building them. Pay $0.10/call via x402 in USDC on Base and get deterministic findings plus a 0-100 score. \"safe\" is not an audit or guarantee.",
  "logoUrl": "/logos/augur.png",
  "websiteUrl": "https://augurrisk.com/",
  "category": "Services/Endpoints"
}
```

## Why This Category

- `Services/Endpoints` matches the upstream category for production APIs with working mainnet x402 integration.
- Augur is a paid HTTP endpoint, not a facilitator, SDK, or learning resource.

## Manual PR Checklist

1. Fork `https://github.com/coinbase/x402`
2. Copy `docs/submissions/x402-ecosystem/metadata.json` into `typescript/site/app/ecosystem/partners-data/augur/metadata.json`
3. Copy `x402JobsAvatar.png` into `typescript/site/public/logos/augur.png`
4. Open a PR titled `Add Augur to x402 ecosystem`
5. After merge, verify `https://www.x402.org/ecosystem` shows Augur and update `docs/REGISTRATIONS.md`

## Blocker

This workspace cannot complete the final upstream GitHub PR by itself. The remaining step is external repository access and PR submission.
