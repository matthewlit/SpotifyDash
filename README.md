# Spotify Account Analytics Dashboard

This dashboard connects directly to your Spotify account using OAuth and shows API-powered analytics in a Spotify-style UI.

## What it shows

- Account profile summary (display name and followers)
- Top tracks and top artists for short / medium / long-term windows
- Popularity and explicit-content metrics
- Top genres inferred from your top artists
- Recent listening activity patterns (hour-of-day)
- Recommendation suggestions based on your top tracks
- CSV export for top tracks, top artists, and recent plays

## Project structure

- `app.py` — Streamlit Spotify API dashboard
- `requirements.txt` — Python dependencies
- `run_dashboard.bat` — one-click launcher for Windows

## Spotify Developer setup

1. Open the Spotify Developer Dashboard: <https://developer.spotify.com/dashboard>
2. Create an app and copy your **Client ID** and **Client Secret**.
3. Add this Redirect URI in your app settings:
   - `https://your-domain.com/spotify/callback` (or any HTTPS URL you control)

Optional (PowerShell env vars):

```powershell
$env:SPOTIPY_CLIENT_ID="your_client_id"
$env:SPOTIPY_CLIENT_SECRET="your_client_secret"
$env:SPOTIPY_REDIRECT_URI="https://your-domain.com/spotify/callback"
```

### Login flow without localhost redirects

1. Start the dashboard.
2. Click **Login with Spotify**.
3. After approval, Spotify redirects to your configured HTTPS URI.
4. Copy the full redirected URL from the browser address bar.
5. Paste it into **Redirected URL or code** in the app and click **Complete login with pasted callback**.

## Run

One-click (Windows):

- Double-click `run_dashboard.bat`

Manual:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Important API limits

- Spotify Web API does **not** provide full lifetime play-by-play history.
- `Top` endpoints are Spotify-computed windows (`short_term`, `medium_term`, `long_term`).
- `Recently Played` is limited to recent listens (not your full history).
