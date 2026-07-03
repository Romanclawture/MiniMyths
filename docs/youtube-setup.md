# YouTube API Setup (one-time, ~10 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/), create a
   project (e.g. `minimyths`).
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **APIs & Services → OAuth consent screen** → External → fill in app name +
   your email. Add yourself as a test user (no verification needed while the
   app stays in testing mode).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID** →
   Application type: **Desktop app**.
5. Download the JSON and save it as `credentials/client_secret.json` in this
   repo (the folder is gitignored).
6. Run `python -m minimyths publish content/hercules`. A browser window opens —
   sign in with the Google account that owns **@Mini_Myths** and approve.
   A token is cached at `credentials/token.json`; you won't be asked again.

Notes
- Uploads default to **private** (set in the channel config) so we can review
  before flipping public.
- Scheduling: `publish --at 2026-07-10T15:00:00Z` uploads private with a
  `publishAt`, and YouTube makes it public at that time automatically.
- Quota: default 10,000 units/day; an upload is 1,600 → ~6 uploads/day max
  without a quota increase. Fine for our cadence.
- **Heads-up:** unverified apps in "testing" mode expire their refresh tokens
  every 7 days. Once uploads are working, either publish the OAuth app
  (verification not required for the upload scope with your own channel) or
  expect a re-auth prompt weekly.
