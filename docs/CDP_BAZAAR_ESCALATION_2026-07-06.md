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
