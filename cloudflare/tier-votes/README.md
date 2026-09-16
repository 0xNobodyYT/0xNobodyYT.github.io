# Sword x Staff Community Tier Votes

Cloudflare Worker and D1 backend for the Community Tier List.

## Endpoints

- `GET /api/health`
- `GET /api/results?tier=T1`
- `POST /api/votes`

The production frontend origin is restricted to `https://0xnobodyyt.github.io`. D1 enforces one ballot for each browser identifier and tier. Browser identifiers are salted and hashed before storage.

## Deploy

```powershell
npx wrangler d1 migrations apply sxs-tier-votes --remote
npx wrangler deploy
npx wrangler secret put VOTER_SALT
```
