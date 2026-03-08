# Augur JavaScript Paid Call Example

Node example for making a paid x402 request to Augur.

## Install

```bash
npm install
```

## Dry Run

See the `402 Payment Required` response without spending funds:

```bash
npm run dry-run
```

## Paid Call

1. Copy `.env.example` to `.env`
2. Set `CLIENT_PRIVATE_KEY`
3. Run:

```bash
npm start
```

## Defaults

- URL: `https://augurrisk.com`
- Contract: `0x4200000000000000000000000000000000000006`

## Custom Target

```bash
node index.mjs --url http://localhost:5000 --address 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 --dry-run
```
