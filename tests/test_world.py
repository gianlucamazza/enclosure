from enclosure.world import Identity, World


def test_clock_and_http_date():
    w = World()
    w.set_clock("2026-06-01T09:00:00Z")
    assert w.get_clock().year == 2026
    assert "Jun 2026" in w.http_date() or "01 Jun 2026" in w.http_date()


def test_publish_versions_and_live_pointer():
    w = World()
    a = w.publish(channel="http", host="ex.test", path="/", body="v1")
    b = w.publish(channel="http", host="ex.test", path="/", body="v2")
    live = w.get_live("http", "ex.test", "/")
    assert live is not None
    assert live.id == b.id
    assert live.version == 2
    assert w.get_by_id(a.id).live is False


def test_http_get_alias_and_trailing_slash():
    w = World()
    w.upsert_identity(
        Identity(
            id="psf",
            kind="official",
            hosts=("www.python.org", "python.org"),
            display_name="PSF",
            chrome="python_org",
            headers={},
        )
    )
    w.publish(
        channel="http",
        host="www.python.org",
        path="/downloads/",
        body="stable",
        identity_id="psf",
    )
    assert w.http_get("python.org", "/downloads/").body == "stable"
    assert w.http_get("www.python.org", "/downloads").body == "stable"
