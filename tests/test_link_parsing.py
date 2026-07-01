from bot.services.spotify_service import extract_track_id, is_spotify_track_url, is_spotify_url
from bot.services.youtube_service import is_youtube_url


def test_youtube_watch_url_detected():
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_youtube_short_url_detected():
    assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")


def test_youtube_shorts_url_detected():
    assert is_youtube_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")


def test_plain_search_text_not_youtube_url():
    assert not is_youtube_url("some artist - some song")


def test_spotify_track_url_detected():
    url = "https://open.spotify.com/track/11dFghVXANMlKmJXsNCbNl"
    assert is_spotify_track_url(url)
    assert is_spotify_url(url)


def test_spotify_playlist_url_not_track():
    url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    assert is_spotify_url(url)
    assert not is_spotify_track_url(url)


def test_extract_track_id():
    url = "https://open.spotify.com/track/11dFghVXANMlKmJXsNCbNl?si=abc123"
    assert extract_track_id(url) == "11dFghVXANMlKmJXsNCbNl"


def test_extract_track_id_returns_none_for_non_spotify():
    assert extract_track_id("https://example.com") is None
