from bot.services.matcher import _score
from bot.services.spotify_service import SpotifyTrack


def _track(duration_seconds: int = 200) -> SpotifyTrack:
    return SpotifyTrack(
        title="Song Title",
        artist="Some Artist",
        album="Some Album",
        duration_seconds=duration_seconds,
        cover_url=None,
    )


def test_close_duration_and_matching_title_scores_higher():
    track = _track(duration_seconds=200)
    good_candidate = {"title": "Some Artist - Song Title", "duration": 202}
    bad_candidate = {"title": "Totally Unrelated Video", "duration": 900}

    assert _score(good_candidate, track) > _score(bad_candidate, track)


def test_missing_duration_is_penalized_but_does_not_crash():
    track = _track(duration_seconds=200)
    candidate = {"title": "Some Artist - Song Title"}

    score = _score(candidate, track)
    assert isinstance(score, float)
