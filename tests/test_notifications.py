"""
tests/test_notifications.py — Mixtape

Tests for notification creation logic. Regression coverage for Issue #4:
rating a friend's song must notify the original sharer, the same way
adding it to a playlist does.
"""

import pytest
from app import create_app, db
from models import User, Song
from services.notification_service import rate_song, get_notifications


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def sharer_and_rater(app):
    """A song shared by one user, to be rated by another."""
    with app.app_context():
        sharer = User(username="sharer", email="sharer@example.com")
        rater = User(username="rater", email="rater@example.com")
        db.session.add_all([sharer, rater])
        db.session.flush()

        song = Song(title="Test Track", artist="Test Artist", shared_by=sharer.id)
        db.session.add(song)
        db.session.commit()

        yield {"sharer": sharer, "rater": rater, "song": song}


def test_rating_a_friends_song_notifies_the_sharer(app, sharer_and_rater):
    """
    Rating a song someone else shared should create a 'song_rated'
    notification for the original sharer — mirroring the notification
    that already fires when a song is added to a playlist.
    """
    with app.app_context():
        sharer = sharer_and_rater["sharer"]
        rater = sharer_and_rater["rater"]
        song = sharer_and_rater["song"]

        assert get_notifications(sharer.id) == []

        rate_song(rater.id, song.id, 5)

        notifications = get_notifications(sharer.id)
        assert len(notifications) == 1
        assert notifications[0]["type"] == "song_rated"
        assert rater.username in notifications[0]["body"]


def test_rating_your_own_song_does_not_self_notify(app, sharer_and_rater):
    """A user rating their own shared song should not generate a notification."""
    with app.app_context():
        sharer = sharer_and_rater["sharer"]
        song = sharer_and_rater["song"]

        rate_song(sharer.id, song.id, 4)

        assert get_notifications(sharer.id) == []


def test_updating_an_existing_rating_notifies_again(app, sharer_and_rater):
    """Changing an existing rating should still notify the sharer."""
    with app.app_context():
        sharer = sharer_and_rater["sharer"]
        rater = sharer_and_rater["rater"]
        song = sharer_and_rater["song"]

        rate_song(rater.id, song.id, 3)
        rate_song(rater.id, song.id, 5)

        notifications = get_notifications(sharer.id)
        assert len(notifications) == 2
