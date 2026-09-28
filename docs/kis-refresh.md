# KIS refresh operation

- KST 06:00 / 12:00 / 15:35 (UTC `0 21 * * *`, `0 3 * * *`, `35 6 * * *`).
- Telegram stays 09:00 / 12:00 / 15:00 / 16:00. Hana stays weekdays 15:35.
- GitHub scheduled jobs may start late; cron is not a guaranteed execution deadline.

The preparation step restores an encrypted token from Actions cache. It reuses a
valid token and permits at most one issuance attempt per rolling 24 hours and KST
calendar day. API errors do not trigger token renewal. Manual test-only runs never
prepare a token. Manual refreshes reuse the same state and cannot initialize a
missing cache. Only the first scheduled morning attempt can initialize it.

The cache contains Fernet ciphertext, encrypted using a domain-separated SHA-256
key derived from the existing KIS key/secret. No extra GitHub Secret is required.
Only ciphertext is cached. Decrypted tokens stay in memory. The cache file is in
`runner.temp/kis-private/token.enc`, outside checkout and Pages artifacts. Local
runs use `%LOCALAPPDATA%/HRC_IR/kis-private/token.enc` (home fallback). No token is
stored in report JSON, Git, plaintext files or log output.

Issuance attempts are recorded before the HTTP request; the workflow saves this
state even after an error and before querying prices. Missing/corrupt/expired
state is never an invitation to retry repeatedly. Cache persistence is required;
if GitHub cannot save/restore it, investigate the failed job rather than repeatedly
rerunning. Deleting the cache deliberately is not a renewal procedure.

On migration from the former in-memory-only implementation, the last successful
market timestamp blocks another issuance within 24h. Today's discarded token
cannot be recovered. The next eligible scheduled run starts the encrypted cache.

Domestic price dates and previous closes come from dated KIS daily rows, with
today's placeholder excluded before 09:00. Investor-flow dates are separate and
shown when different. A missing price pair fails without overwriting the last
successful market snapshot. Tests use synthetic tokens; they never contact KIS.
