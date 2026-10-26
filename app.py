from __future__ import annotations

import os
from importlib import import_module
from importlib.util import find_spec
from urllib.parse import parse_qs, urlparse

import pandas as pd
import plotly.express as px
import streamlit as st

if find_spec("spotipy") is not None:
    spotipy = import_module("spotipy")
else:
    spotipy = None

st.set_page_config(page_title="Spotify Account Dashboard", page_icon="🎧", layout="wide")


def apply_spotify_theme() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: linear-gradient(180deg, #121212 0%, #191414 100%);
                color: #FFFFFF;
            }
            section[data-testid="stSidebar"] {
                background: #0F0F0F;
                border-right: 1px solid #2A2A2A;
            }
            div[data-testid="stMetric"] {
                background: rgba(29, 185, 84, 0.12);
                border: 1px solid rgba(29, 185, 84, 0.35);
                border-radius: 12px;
                padding: 10px 12px;
            }
            .spotify-pill {
                display: inline-block;
                border-radius: 999px;
                padding: 6px 12px;
                font-weight: 600;
                background: #1DB954;
                color: #121212;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=True)
def fetch_top_tracks(access_token: str, time_range: str) -> pd.DataFrame:
    if spotipy is None:
        return pd.DataFrame()

    client = spotipy.Spotify(auth=access_token, requests_timeout=15, retries=3)
    items = client.current_user_top_tracks(limit=50, offset=0, time_range=time_range).get("items", [])

    rows: list[dict[str, object]] = []
    for idx, track in enumerate(items, start=1):
        artists = track.get("artists", []) or []
        rows.append(
            {
                "rank": idx,
                "track_id": track.get("id"),
                "track_name": track.get("name"),
                "artist_names": ", ".join(a.get("name", "") for a in artists if a.get("name")),
                "album_name": (track.get("album") or {}).get("name"),
                "release_date": (track.get("album") or {}).get("release_date"),
                "popularity": track.get("popularity", 0),
                "duration_min": round((track.get("duration_ms", 0) or 0) / 60000, 2),
                "explicit": bool(track.get("explicit", False)),
                "uri": track.get("uri"),
                "external_url": (track.get("external_urls") or {}).get("spotify", ""),
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=True)
def fetch_top_artists(access_token: str, time_range: str) -> pd.DataFrame:
    if spotipy is None:
        return pd.DataFrame()

    client = spotipy.Spotify(auth=access_token, requests_timeout=15, retries=3)
    items = client.current_user_top_artists(limit=50, offset=0, time_range=time_range).get("items", [])

    rows: list[dict[str, object]] = []
    for idx, artist in enumerate(items, start=1):
        rows.append(
            {
                "rank": idx,
                "artist_id": artist.get("id"),
                "artist_name": artist.get("name"),
                "popularity": artist.get("popularity", 0),
                "followers": (artist.get("followers") or {}).get("total", 0),
                "genres": artist.get("genres", []),
                "external_url": (artist.get("external_urls") or {}).get("spotify", ""),
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=True)
def fetch_recent_plays(access_token: str, limit: int = 50) -> pd.DataFrame:
    if spotipy is None:
        return pd.DataFrame()

    client = spotipy.Spotify(auth=access_token, requests_timeout=15, retries=3)
    response = client.current_user_recently_played(limit=limit)
    items = response.get("items", [])

    rows: list[dict[str, object]] = []
    for item in items:
        track = item.get("track") or {}
        artists = track.get("artists", []) or []
        played_at = pd.to_datetime(item.get("played_at"), utc=True, errors="coerce")
        rows.append(
            {
                "played_at": played_at,
                "track_name": track.get("name"),
                "artist_names": ", ".join(a.get("name", "") for a in artists if a.get("name")),
                "album_name": (track.get("album") or {}).get("name"),
                "popularity": track.get("popularity", 0),
                "duration_min": round((track.get("duration_ms", 0) or 0) / 60000, 2),
                "explicit": bool(track.get("explicit", False)),
                "uri": track.get("uri"),
                "external_url": (track.get("external_urls") or {}).get("spotify", ""),
            }
        )

    recent = pd.DataFrame(rows)
    if recent.empty:
        return recent

    recent = recent.dropna(subset=["played_at"]).copy()
    recent["weekday"] = recent["played_at"].dt.day_name()
    recent["hour"] = recent["played_at"].dt.hour
    return recent


@st.cache_data(show_spinner=False)
def fetch_recommendations(access_token: str, seed_track_ids: tuple[str, ...]) -> pd.DataFrame:
    if spotipy is None or not seed_track_ids:
        return pd.DataFrame()

    client = spotipy.Spotify(auth=access_token, requests_timeout=15, retries=3)
    response = client.recommendations(seed_tracks=list(seed_track_ids)[:5], limit=20)
    items = response.get("tracks", [])

    rows: list[dict[str, object]] = []
    for track in items:
        artists = track.get("artists", []) or []
        rows.append(
            {
                "track_name": track.get("name"),
                "artist_names": ", ".join(a.get("name", "") for a in artists if a.get("name")),
                "popularity": track.get("popularity", 0),
                "album_name": (track.get("album") or {}).get("name"),
                "external_url": (track.get("external_urls") or {}).get("spotify", ""),
            }
        )
    return pd.DataFrame(rows)


def _get_spotify_oauth(client_id: str, client_secret: str, redirect_uri: str):
    if spotipy is None:
        return None

    spotify_oauth_cls = getattr(import_module("spotipy.oauth2"), "SpotifyOAuth")
    return spotify_oauth_cls(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="user-top-read user-read-recently-played user-read-email user-read-private",
        open_browser=False,
        cache_path=None,
        show_dialog=False,
    )


def _extract_auth_code(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        query = parse_qs(parsed.query)
        return (query.get("code") or [""])[0]

    return raw


def _get_token_info(auth_manager):
    token_info = st.session_state.get("spotify_token_info")
    if token_info and not auth_manager.is_token_expired(token_info):
        return token_info

    if token_info and token_info.get("refresh_token"):
        refreshed = auth_manager.refresh_access_token(token_info["refresh_token"])
        st.session_state["spotify_token_info"] = refreshed
        return refreshed

    code = st.query_params.get("code")
    if not code:
        manual_value = st.session_state.get("spotify_manual_callback", "")
        code = _extract_auth_code(manual_value)

    if code:
        fetched = auth_manager.get_access_token(code=code, check_cache=False)
        st.session_state["spotify_token_info"] = fetched
        st.session_state.pop("spotify_manual_callback", None)
        st.query_params.clear()
        st.rerun()
    return None


@st.cache_data(show_spinner=False)
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def main() -> None:
    apply_spotify_theme()
    st.title("Spotify Account Analytics Dashboard")
    st.caption("API-powered analytics from your Spotify account (no extended history files required)")

    if spotipy is None:
        st.error("Spotipy is not installed. Run: python -m pip install -r requirements.txt")
        return

    st.sidebar.header("Spotify Account")
    client_id = st.sidebar.text_input("Client ID", value=os.getenv("SPOTIPY_CLIENT_ID", ""))
    client_secret = st.sidebar.text_input(
        "Client Secret",
        value=os.getenv("SPOTIPY_CLIENT_SECRET", ""),
        type="password",
    )
    redirect_uri = st.sidebar.text_input(
        "Redirect URI",
        value=os.getenv("SPOTIPY_REDIRECT_URI", "https://example.com/spotify/callback"),
    )

    time_range_display = st.sidebar.selectbox(
        "Top data window",
        ["Last 4 Weeks", "Last 6 Months", "All Available Time"],
        index=2,
    )
    time_range_map = {
        "Last 4 Weeks": "short_term",
        "Last 6 Months": "medium_term",
        "All Available Time": "long_term",
    }
    time_range = time_range_map[time_range_display]

    if st.sidebar.button("Log out"):
        st.session_state.pop("spotify_token_info", None)
        st.session_state.pop("spotify_manual_callback", None)
        st.query_params.clear()
        st.rerun()

    if not client_id or not client_secret or not redirect_uri:
        st.info("Enter Spotify API credentials in the sidebar to connect your account.")
        return

    auth_manager = _get_spotify_oauth(client_id, client_secret, redirect_uri)
    if auth_manager is None:
        st.error("Spotify OAuth setup failed. Check dependencies and credentials.")
        return

    try:
        token_info = _get_token_info(auth_manager)
    except Exception as exc:
        st.error(f"OAuth token error: {exc}")
        return

    if not token_info:
        login_url = auth_manager.get_authorize_url()
        st.markdown('<span class="spotify-pill">Connect Spotify to continue</span>', unsafe_allow_html=True)
        st.link_button("Login with Spotify", login_url, use_container_width=False)

        st.markdown("#### Manual callback (for non-localhost redirect URIs)")
        st.caption(
            "After approving access, copy the full redirected URL (or just the `code` value) and paste it below."
        )
        manual_callback = st.text_input(
            "Redirected URL or code",
            value=st.session_state.get("spotify_manual_callback", ""),
            placeholder="https://your-redirect-domain/callback?code=...",
        )
        if st.button("Complete login with pasted callback"):
            st.session_state["spotify_manual_callback"] = manual_callback
            st.rerun()

        st.caption("Automatic callback still works if your redirect URI points to this app URL.")
        return

    access_token = token_info.get("access_token", "")
    if not access_token:
        st.error("Could not obtain access token from Spotify.")
        return

    client = spotipy.Spotify(auth=access_token, requests_timeout=15, retries=3)
    try:
        profile = client.current_user()
        top_tracks = fetch_top_tracks(access_token, time_range)
        top_artists = fetch_top_artists(access_token, time_range)
        recent = fetch_recent_plays(access_token, limit=50)
    except Exception as exc:
        st.error(f"Spotify API request failed: {exc}")
        return

    display_name = profile.get("display_name") or "Spotify User"
    followers = int((profile.get("followers") or {}).get("total", 0))
    st.markdown(f"### Welcome, {display_name}")

    avg_track_pop = float(top_tracks["popularity"].mean()) if not top_tracks.empty else 0.0
    avg_artist_pop = float(top_artists["popularity"].mean()) if not top_artists.empty else 0.0
    explicit_share = float(top_tracks["explicit"].mean() * 100) if not top_tracks.empty else 0.0
    recent_unique_artists = int(recent["artist_names"].nunique()) if not recent.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Followers", f"{followers:,}")
    c2.metric("Top Tracks Loaded", f"{len(top_tracks):,}")
    c3.metric("Top Artists Loaded", f"{len(top_artists):,}")
    c4.metric("Avg Track Popularity", f"{avg_track_pop:,.1f}/100")
    c5.metric("Explicit Share", f"{explicit_share:,.1f}%")

    st.markdown("---")

    left, right = st.columns(2)
    with left:
        st.subheader("Top Tracks by Popularity")
        if not top_tracks.empty:
            chart_tracks = top_tracks.head(20).copy()
            chart_tracks["label"] = chart_tracks["track_name"] + " — " + chart_tracks["artist_names"]
            fig_tracks = px.bar(
                chart_tracks.sort_values("popularity"),
                x="popularity",
                y="label",
                orientation="h",
                labels={"popularity": "Popularity", "label": "Track"},
                color="popularity",
                color_continuous_scale="Greens",
            )
            fig_tracks.update_layout(margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
            st.plotly_chart(fig_tracks, use_container_width=True)
        else:
            st.info("No top tracks returned for this time window.")

    with right:
        st.subheader("Top Artists by Popularity")
        if not top_artists.empty:
            fig_artists = px.bar(
                top_artists.head(20).sort_values("popularity"),
                x="popularity",
                y="artist_name",
                orientation="h",
                labels={"popularity": "Popularity", "artist_name": "Artist"},
                color="popularity",
                color_continuous_scale="Greens",
            )
            fig_artists.update_layout(margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
            st.plotly_chart(fig_artists, use_container_width=True)
        else:
            st.info("No top artists returned for this time window.")

    st.markdown("---")

    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Top Genres from Top Artists")
        if not top_artists.empty and "genres" in top_artists.columns:
            genres = top_artists[["genres"]].explode("genres").dropna()
            if not genres.empty:
                genre_counts = genres["genres"].value_counts().head(20).reset_index()
                genre_counts.columns = ["genre", "artist_count"]
                fig_genres = px.bar(
                    genre_counts.sort_values("artist_count"),
                    x="artist_count",
                    y="genre",
                    orientation="h",
                    labels={"artist_count": "Count in Top Artists", "genre": "Genre"},
                    color="artist_count",
                    color_continuous_scale="Greens",
                )
                fig_genres.update_layout(margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
                st.plotly_chart(fig_genres, use_container_width=True)
            else:
                st.info("No genre metadata available in the selected window.")
        else:
            st.info("No genre metadata available in the selected window.")

    with g2:
        st.subheader("Recent Listening by Hour")
        if not recent.empty:
            hour_data = recent.groupby("hour", as_index=False).size().rename(columns={"size": "plays"})
            fig_hour = px.bar(
                hour_data,
                x="hour",
                y="plays",
                labels={"hour": "Hour (0-23)", "plays": "Recent Plays"},
                color="plays",
                color_continuous_scale="Greens",
            )
            fig_hour.update_layout(margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
            st.plotly_chart(fig_hour, use_container_width=True)
            st.metric("Unique Artists in Recent Plays", f"{recent_unique_artists:,}")
        else:
            st.info("No recent plays available (Spotify API returns the latest ~50 listens).")

    st.markdown("---")

    st.subheader("Discovery Suggestions")
    seed_ids = tuple(top_tracks["track_id"].dropna().astype(str).head(5).tolist()) if not top_tracks.empty else tuple()
    suggestions = fetch_recommendations(access_token, seed_ids)
    if not suggestions.empty:
        st.caption("Generated from your top tracks using Spotify recommendations.")
        st.dataframe(suggestions, use_container_width=True, hide_index=True)
    else:
        st.info("No recommendations available yet. Try again after Spotify top tracks load.")

    st.markdown("---")

    t1, t2 = st.columns(2)
    with t1:
        st.subheader("Top Tracks Table")
        st.download_button(
            "Download top tracks CSV",
            data=to_csv_bytes(top_tracks),
            file_name=f"spotify_top_tracks_{time_range}.csv",
            mime="text/csv",
            disabled=top_tracks.empty,
        )
        st.dataframe(top_tracks, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("Top Artists Table")
        st.download_button(
            "Download top artists CSV",
            data=to_csv_bytes(top_artists),
            file_name=f"spotify_top_artists_{time_range}.csv",
            mime="text/csv",
            disabled=top_artists.empty,
        )
        st.dataframe(top_artists, use_container_width=True, hide_index=True)

    if not recent.empty:
        st.subheader("Recent Plays")
        st.download_button(
            "Download recent plays CSV",
            data=to_csv_bytes(recent),
            file_name="spotify_recent_plays.csv",
            mime="text/csv",
        )
        st.dataframe(recent.sort_values("played_at", ascending=False), use_container_width=True, hide_index=True)

    st.caption(
        "Note: Spotify Web API does not expose full historical lifetime play-by-play data. "
        "Top endpoints return Spotify's calculated windows (short/medium/long term), and recent plays are limited."
    )


if __name__ == "__main__":
    main()
