# CDP Bazaar Escalation Packet - 2026-07-06

## Issue

CDP Bazaar still indexes Augur under the dead Conway URL instead of the canonical production URL.

- Stale indexed resource: `https://risk-api.life.conway.tech/analyze`
- Canonical resource: `https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006`
- Merchant payTo: `0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`
- Payer used for repair smoke: `0x79301Cf19Aaea29fbe40F0F5B78F73e2c3b0a2b8`

## Evidence

### 1. Canonical endpoint validates

CDP read-only validation endpoint:

```powershell
POST https://api.cdp.coinbase.com/platform/v2/x402/validate
resource=https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006
method=GET
```

Result on 2026-07-06:

- `status_code=200`
- `valid=True`
- `statusCode=402`
- `x402Version=2`
- `has_bazaar_extension=True`
- required checks passed:
  - `url_valid`
  - `url_https`
  - `endpoint_reachable`
  - `returns_402`
  - `valid_json`
  - `x402_version`
  - `payment_required_header`
  - `has_accepts`
  - `has_resource`
  - `has_bazaar_extension`
  - `bazaar.info`
  - `bazaar.info.input`
  - `bazaar.schema`
  - `parse`

### 2. Fresh successful settlement completed

On 2026-07-06, a real paid WETH smoke call succeeded:

```powershell
python scripts\test_x402_payment.py
```

Result:

- response `200`
- score `0`
- level `safe`
- findings `0`
- paid amount `0.100000 USDC`

Blockscout token-transfer evidence:

- tx: `0x38d86ab18f54029a8e453c50a0bb3adcfb37a05dfc165dc32305f666427f218d`
- timestamp: `1783376229`
- from: `0x79301cf19aaea29fbe40f0f5b78f73e2c3b0a2b8`
- to: `0x13580b9c6a9afbfe4c739e74136c1da174db9891`
- amount: `0.1 USDC`

### 3. CDP discovery still returns stale Conway resource

Fresh catalog scan:

```powershell
python scripts\check_cdp_discovery.py
```

Result on 2026-07-06:

- scanned `200` pages / `20,000` items
- canonical `https://augurrisk.com/analyze` not found
- stale related match still present: `https://risk-api.life.conway.tech/analyze`

Merchant endpoint:

```text
GET https://api.cdp.coinbase.com/platform/v2/x402/discovery/merchant?payTo=0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891
```

Result:

- `total=1`
- only resource: `https://risk-api.life.conway.tech/analyze`
- `lastUpdated=2026-03-02T05:26:45.981Z`
- `l30DaysTotalCalls=0`
- `l30DaysUniquePayers=0`

Search endpoint:

```text
GET /platform/v2/x402/discovery/search?urlSubstring=augurrisk.com
```

Result:

- `0` resources

```text
GET /platform/v2/x402/discovery/search?urlSubstring=risk-api.life.conway.tech
```

Result:

- `1` resource: `https://risk-api.life.conway.tech/analyze`

## Requested CDP/Bazaar Action

Please remove or refresh the stale `risk-api.life.conway.tech/analyze` resource and index the canonical `augurrisk.com` resource for the same merchant payTo:

```text
https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006
```

The canonical endpoint passes CDP validation and has a fresh successful CDP-facilitated x402 settlement.

## 2026-07-07 Recheck

The delayed index did not self-repair overnight.

Commands:

```powershell
python scripts\check_cdp_discovery.py --max-pages 200
GET https://api.cdp.coinbase.com/platform/v2/x402/discovery/merchant?payTo=0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891&limit=20
GET https://api.cdp.coinbase.com/platform/v2/x402/discovery/search?urlSubstring=augurrisk.com&limit=20
GET https://api.cdp.coinbase.com/platform/v2/x402/discovery/search?urlSubstring=risk-api.life.conway.tech&limit=20
python scripts\register_x402jobs.py --list --search Augur
```

Results:

- full CDP scan: `scanned_pages=200`, `scanned_items=20000`, `status=NOT_FOUND`
- stale related match still present: `https://risk-api.life.conway.tech/analyze`
- merchant discovery for payTo returned only `https://risk-api.life.conway.tech/analyze`
- merchant `lastUpdated` stayed `2026-03-02T05:26:45.981Z`
- CDP search `urlSubstring=augurrisk.com` returned no resources
- CDP search `urlSubstring=risk-api.life.conway.tech` returned `https://risk-api.life.conway.tech/analyze`
- x402.jobs is still repaired as `https://x402.jobs/resources/augurrisk-com/augur-2`

Official escalation destinations found on 2026-07-07:

1. CDP support form: `https://support.cdp.coinbase.com/`
2. CDP/x402 Discord: `https://discord.gg/cdp`
3. x402 GitHub issues: `https://github.com/x402-foundation/x402/issues`

Practical route: use CDP support first, then post the same message in the CDP Discord x402 support/community channel if no ticket response. GitHub Issues is official for bug reports, but the public repo page currently shows issue creation as restricted, so it is not the primary route unless the user account has permission.

## Copy-Paste Support Message

Subject:

```text
CDP Bazaar stale resource: Augur still indexed at dead Conway URL after canonical validation and settlement
```

Body:

```text
Hi CDP/x402 team,

I operate Augur, an x402-paid Base contract risk API.

CDP Bazaar still indexes Augur under a dead legacy URL:
https://risk-api.life.conway.tech/analyze

The canonical production URL is:
https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006

Merchant payTo:
0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891

Evidence:
- The canonical endpoint passed CDP /platform/v2/x402/validate on 2026-07-06 with valid=True, statusCode=402, x402Version=2, and Bazaar extension present.
- A real paid CDP-facilitated x402 call succeeded on 2026-07-06.
- Blockscout USDC transfer tx:
  0x38d86ab18f54029a8e453c50a0bb3adcfb37a05dfc165dc32305f666427f218d
- On 2026-07-07, a 20,000-resource CDP discovery scan still did not find augurrisk.com/analyze and still returned the stale Conway URL as the only Augur-related match.
- CDP merchant discovery for payTo 0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891 still returns only https://risk-api.life.conway.tech/analyze with lastUpdated=2026-03-02T05:26:45.981Z.
- CDP search urlSubstring=augurrisk.com returns no resources.
- CDP search urlSubstring=risk-api.life.conway.tech returns the stale resource.

Could you remove or refresh the stale Conway resource and index the canonical Augur resource at augurrisk.com for the same payTo?

Thanks.
```
