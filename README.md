# Harf Captions — backend

Sindhi/Urdu/English YouTube caption generator with Google sign-in and
a paid subscription. Pipeline: audio in, corrected + burned-in
captioned video out.

## Structure

```
caption-tool/
  main.py                    entry point, FastAPI app, CORS, creates DB tables
  requirements.txt
  .env.example                copy to .env and fill in real keys
  app/
    config.py                 loads all settings from .env
    database.py                SQLAlchemy engine/session (SQLite by default)
    auth.py                    verifies Google sign-in, issues/reads our session JWT
    routers/
      auth_router.py           POST /auth/google — trades a Google credential for a session token
      billing.py                POST /billing/checkout, POST /billing/webhook, GET /billing/status
      captions.py                POST /captions/from-upload, /from-youtube, GET /captions/usage, /download
    services/
      downloader.py             yt-dlp: pulls audio from a YouTube link, or saves an upload
      transcriber.py            Whisper: raw timestamped transcript (any language)
      corrector.py               Claude: rewrites lines into clean Sindhi/Urdu/English script
      subtitle_writer.py         formats corrected lines into .srt or .vtt
      video_burner.py            ffmpeg: burns the corrected subtitles into the video itself
      usage.py                   daily free-video counting and enforcement
    models/
      schemas.py                 request/response shapes
      db_models.py                User and UsageRecord tables
```

## Pipeline

1. Sign in with Google (frontend) -> `/auth/google` verifies it and
   returns a session token the frontend keeps for every later request.
2. `/captions/from-upload` checks `usage.py` — signed-in, non-subscribed
   users get `FREE_DAILY_VIDEOS` (default 2) per day; subscribed users
   are unlimited. Over the limit returns HTTP 402.
3. `downloader.py` saves the upload (or pulls audio from a YouTube link).
4. `transcriber.py` sends it to Whisper for a raw timestamped transcript.
5. `corrector.py` sends the raw lines to Claude, which rewrites them
   into natural Sindhi, Urdu, or English, without changing line count
   (so timestamps stay valid).
6. `subtitle_writer.py` writes the corrected lines to `.srt`.
7. `video_burner.py` burns that `.srt` directly into the video with
   ffmpeg, so the app hands back one finished, downloadable video.
8. The request is logged in `usage_records` so the daily count is accurate.

## Running it locally (Termux or any Linux shell)

```
pip install -r requirements.txt
cp .env.example .env        # fill in the keys below
python main.py
```

Minimum keys to fill in `.env` to run anything at all:
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`. Google sign-in and Stripe need
their own setup — see below — but the server will still start without
them; those routes just won't work until configured.

## Setting up Google Sign-In

1. https://console.cloud.google.com/apis/credentials -> Create
   Credentials -> OAuth client ID -> Application type: Web application.
2. Under "Authorized JavaScript origins" add every URL you'll load the
   frontend from (e.g. `http://localhost:5500` while testing, then your
   real domain later).
3. Copy the Client ID into `GOOGLE_CLIENT_ID` in `.env`, and into the
   `GOOGLE_CLIENT_ID` constant at the top of the frontend's `<script>`.

## Setting up Stripe subscriptions

1. https://dashboard.stripe.com -> Products -> add a product with a
   recurring **monthly** price (this is your subscription price) ->
   copy its Price ID into `STRIPE_PRICE_ID`.
2. https://dashboard.stripe.com/apikeys -> copy the secret key into
   `STRIPE_SECRET_KEY`.
3. https://dashboard.stripe.com/webhooks -> Add endpoint ->
   `https://your-backend-url/billing/webhook` -> select event
   `checkout.session.completed` (and optionally
   `customer.subscription.deleted`, `invoice.payment_failed`) -> copy
   the signing secret into `STRIPE_WEBHOOK_SECRET`.
4. Set `FRONTEND_URL` to wherever the app is hosted, so Stripe knows
   where to send users back after checkout.
5. Test with Stripe's test card `4242 4242 4242 4242` before going live.

## Video burn-in

`services/video_burner.py` needs ffmpeg installed on whatever machine
runs the server (see deployment below). If ffmpeg isn't available,
`video_download_path` comes back `null` and the caller still gets the
`.srt` file as a fallback.

## Deploying the backend (Render.com free tier)

1. Push this `caption-tool/` folder to a GitHub repo.
2. On Render: New -> Web Service -> connect the repo.
3. Build command: `apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add every variable from `.env.example` as an environment variable in
   Render's dashboard (never commit `.env` itself).
6. **Important**: Render's free tier wipes local disk on every
   redeploy, which would delete the SQLite user database. Fine for
   your initial test, but before a public launch, set `DATABASE_URL`
   to a free hosted Postgres (Supabase's free tier works well) so
   accounts and subscriptions survive redeploys.
7. Once deployed you'll get a URL like `https://harf-captions.onrender.com`
   — update the Stripe webhook URL and the Google OAuth "authorized
   origins" to match it, and note it for the frontend.

## Wiring and deploying the frontend

Open the working UI file and set the three constants at the top of
the `<script>` block: `API_BASE_URL` (your Render URL),
`GOOGLE_CLIENT_ID`. Then host that single HTML file anywhere static —
Netlify, Vercel, GitHub Pages, or a Blogger page all work since it's
one self-contained file.

Test on the free subdomain first (e.g. `yourapp.netlify.app`): sign
in with Google, upload a short video, confirm the daily counter drops
and the upgrade screen appears after your free videos are used, and
test a Stripe checkout with the test card above. Only once all of
that works, attach your real custom domain from that host's
settings — remember to also add that domain to Google's "authorized
origins" and, if you change it, to `ALLOWED_ORIGIN` and `FRONTEND_URL`
in the backend's environment variables, then redeploy.

## Security checklist before a public launch

1. Set `ALLOWED_ORIGIN` to your real domain (not `*`) so only your own
   frontend can call the API and spend your OpenAI/Anthropic credits.
2. Set `JWT_SECRET` to a real random value (`openssl rand -hex 32`),
   not the placeholder.
3. Put the backend behind Cloudflare (free plan): point your domain's
   DNS through Cloudflare, which gives free SSL, DDoS protection, and
   hides your origin server's IP. Enable a basic rate-limiting rule on
   `/captions/*` as an extra layer on top of the daily-limit check
   already enforced in `usage.py`.
4. Move `DATABASE_URL` off local SQLite to hosted Postgres before
   launch, per the Render note above.
5. Move file storage off local disk (Cloudflare R2 or Supabase
   Storage) for the same reason — otherwise generated videos disappear
   on every redeploy too.

## Security fixes in this build
- Download endpoints require a valid JWT and verify that the job belongs to the signed-in user.
- Uploads validate extension, file size, and actual media readability with `ffprobe`.
- YouTube input is restricted to YouTube hosts and playlists are disabled.
- Free-tier duration is enforced using `FREE_TIER_MAX_MINUTES`.
- Usage is reserved before expensive AI processing rather than recorded only after success.
- Old job folders are cleaned on application startup after 24 hours.
- Google login requires a verified email and a configured OAuth client ID.
- JWT secret is required from environment configuration; do not use the old `change-me...` default.
- Frontend downloads use authenticated fetch/blob URLs so protected download endpoints still work in the browser.
- Frontend now has real drag-and-drop file handling and validates supported formats.
- Caption correction validates JSON shape and exact line count.


## Frontend configuration
The frontend now keeps deployment values in one small file: `config.js`. Before publishing the frontend, edit only these two values:
- `API_BASE_URL` = your deployed Render backend URL
- `GOOGLE_CLIENT_ID` = your Google OAuth Web Client ID

Keep `config.js` in the same folder as `caption-io-working.html`.
