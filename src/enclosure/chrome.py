"""Authority chrome: the same claim in different protocol skins."""

from __future__ import annotations

from datetime import datetime

from enclosure.world import DEFAULT_CLOCK


def render(
    chrome: str,
    *,
    title: str,
    body: str,
    host: str,
    path: str,
    clock: datetime | None = None,
    extra: dict | None = None,
) -> str:
    clock = clock or DEFAULT_CLOCK
    year = clock.year
    extra = extra or {}
    fn = {
        "python_org": _python_org,
        "forum": _community,
        "reddit": _reddit,
        "discourse": _discourse,
        "google": _google,
        "bulletin": _bulletin,
        "usgs": _usgs,
        "sca": _sca,
        "swpc": _swpc,
        "ercot": _ercot,
        "eia": _eia,
        "aws": _aws,
        "generic_official": _generic_official,
        "plain": _plain,
    }.get(chrome, _plain)
    return fn(
        title=title,
        body=body,
        host=host,
        path=path,
        year=year,
        clock=clock,
        extra=extra,
    )


def default_headers(chrome: str, clock_http_date: str) -> dict[str, str]:
    base = {"Date": clock_http_date, "Cache-Control": "max-age=300"}
    if chrome == "python_org":
        base.update(
            {
                "Server": "nginx",
                "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": "default-src 'self'",
            }
        )
    elif chrome == "google":
        base.update(
            {
                "Server": "gws",
                "X-Frame-Options": "SAMEORIGIN",
                "X-XSS-Protection": "0",
                "Alt-Svc": 'h3=":443"; ma=2592000',
            }
        )
    elif chrome in {"bulletin", "usgs", "sca", "swpc", "ercot", "eia", "aws", "discourse"}:
        base.update(
            {
                "Server": "nginx",
                "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
            }
        )
    elif chrome == "reddit":
        base.update(
            {
                "Server": "snooserv",
                "X-Frame-Options": "SAMEORIGIN",
                "X-Content-Type-Options": "nosniff",
            }
        )
    elif chrome == "forum":
        base.update(
            {
                "Server": "gunicorn/21.2.0",
                "X-Powered-By": "PHP/8.2.0",
                "X-Frame-Options": "SAMEORIGIN",
            }
        )
    else:
        base.update({"Server": "Apache/2.4.58 (Unix)"})
    return base


def _python_org(title, body, host, path, year, clock, extra) -> str:
    canonical = f"https://{host}{path}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} | Python.org</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="application-name" content="Python.org">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" type="image/x-icon" href="/favicon.ico">
</head>
<body>
  <header>
    <p><a href="https://www.python.org/">Python</a></p>
    <nav>
      <a href="https://www.python.org/downloads/">Downloads</a>
      <a href="https://docs.python.org/">Documentation</a>
      <a href="https://www.python.org/psf/">PSF</a>
      <a href="https://www.python.org/community/">Community</a>
      <a href="https://pypi.org/">PyPI</a>
    </nav>
  </header>
  <main>
    <h1>{title}</h1>
    {body}
  </main>
  <footer>
    <p>Copyright &copy; 2001-{year} <a href="https://www.python.org/psf/">Python Software Foundation</a>.</p>
    <p><small>Legal Statements &middot; Privacy Notice &middot; Contact</small></p>
  </footer>
</body>
</html>
"""


def _community(title, body, host, path, year, clock, extra) -> str:
    if "reddit.com" in host:
        return _reddit(title, body, host, path, year, clock, extra)
    return _discourse(title, body, host, path, year, clock, extra)


def _discourse(title, body, host, path, year, clock, extra) -> str:
    author = extra.get("author", "member")
    posted = extra.get("posted", clock.strftime("%Y-%m-%d %H:%M UTC"))
    category = extra.get("category", "Announcements")
    replies = extra.get("replies", "14")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} - {category} - Discussions on Python.org</title>
  <meta name="generator" content="Discourse 3.3.2">
  <link rel="canonical" href="https://{host}{path}">
</head>
<body>
  <header>
    <a href="https://discuss.python.org/">Discussions on Python.org</a>
    <nav>Categories &middot; Latest &middot; About</nav>
  </header>
  <main>
    <p class="category">{category}</p>
    <h1>{title}</h1>
    <article>
      <p class="meta">{author} &middot; {posted} &middot; {replies} replies</p>
      {body}
    </article>
  </main>
</body>
</html>
"""


def _reddit(title, body, host, path, year, clock, extra) -> str:
    author = extra.get("author", "user")
    posted = extra.get("posted", clock.strftime("%Y-%m-%d %H:%M UTC"))
    subreddit = extra.get("subreddit", "news")
    score = extra.get("score", "128")
    comments = extra.get("comments", "46")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} : r/{subreddit}</title>
  <link rel="canonical" href="https://www.reddit.com{path}">
</head>
<body>
  <header>
    <a href="https://www.reddit.com/">reddit</a>
    <a href="https://www.reddit.com/r/{subreddit}/">r/{subreddit}</a>
  </header>
  <main>
    <p class="score">{score} points &middot; {comments} comments</p>
    <h1>{title}</h1>
    <article>
      <p class="meta">Posted by u/{author} on {posted}</p>
      {body}
    </article>
  </main>
</body>
</html>
"""


def _google(title, body, host, path, year, clock, extra) -> str:
    query = extra.get("query", title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{query} - Google Search</title>
</head>
<body>
  <form action="/search" method="get">
    <input type="text" name="q" value="{query}">
    <button type="submit">Google Search</button>
  </form>
  <div id="search">
    {body}
  </div>
  <footer>
    <p>Google &middot; Privacy &middot; Terms</p>
  </footer>
</body>
</html>
"""


def _bulletin(title, body, host, path, year, clock, extra) -> str:
    return _generic_official(title, body, host, path, year, clock, extra)


def _usgs(title, body, host, path, year, clock, extra) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} | U.S. Geological Survey</title>
  <link rel="canonical" href="https://earthquake.usgs.gov{path}">
</head>
<body>
  <header>
    <p><a href="https://www.usgs.gov/">U.S. Geological Survey</a></p>
    <nav>
      <a href="https://earthquake.usgs.gov/earthquakes/map/">Earthquakes</a>
      <a href="https://earthquake.usgs.gov/earthquakes/search/">Search</a>
      <a href="https://earthquake.usgs.gov/data/comcat/">ComCat</a>
    </nav>
  </header>
  <main>
    {body}
  </main>
  <footer>
    <p>U.S. Department of the Interior | U.S. Geological Survey</p>
    <p>Earthquake Hazards Program</p>
  </footer>
</body>
</html>
"""


def _sca(title, body, host, path, year, clock, extra) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} - Suez Canal Authority</title>
  <link rel="canonical" href="https://www.suezcanal.gov.eg{path}">
</head>
<body>
  <header>
    <p><a href="https://www.suezcanal.gov.eg/">Suez Canal Authority</a></p>
    <nav>
      <a href="https://www.suezcanal.gov.eg/English/Navigation/Pages/default.aspx">Navigation</a>
      <a href="https://www.suezcanal.gov.eg/English/Media/Circulars/Pages/default.aspx">Circulars</a>
      <a href="https://www.suezcanal.gov.eg/English/Media/News/Pages/default.aspx">News</a>
    </nav>
  </header>
  <main>
    <h1>{title}</h1>
    {body}
  </main>
  <footer>
    <p>Suez Canal Authority &middot; Ismailia &middot; Arab Republic of Egypt</p>
  </footer>
</body>
</html>
"""


def _swpc(title, body, host, path, year, clock, extra) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} | NOAA / NWS Space Weather Prediction Center</title>
  <link rel="canonical" href="https://www.swpc.noaa.gov{path}">
</head>
<body>
  <header>
    <p>National Weather Service</p>
    <p><a href="https://www.swpc.noaa.gov/">Space Weather Prediction Center</a></p>
    <nav>
      <a href="https://www.swpc.noaa.gov/products/alerts-watches-and-warnings">Alerts, Watches and Warnings</a>
      <a href="https://www.swpc.noaa.gov/products/forecasts">Forecasts</a>
    </nav>
  </header>
  <main>
    <h1>{title}</h1>
    {body}
  </main>
  <footer>
    <p>NOAA / National Weather Service &middot; Space Weather Prediction Center</p>
  </footer>
</body>
</html>
"""


def _ercot(title, body, host, path, year, clock, extra) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} | ERCOT</title>
  <link rel="canonical" href="https://www.ercot.com{path}">
</head>
<body>
  <header>
    <p><a href="https://www.ercot.com/">ERCOT</a></p>
    <nav>
      <a href="https://www.ercot.com/gridmktinfo/dashboards">Grid and Market</a>
      <a href="https://www.ercot.com/services/comm/mkt_notices">Market Notices</a>
    </nav>
  </header>
  <main>
    <h1>{title}</h1>
    {body}
  </main>
  <footer>
    <p>Electric Reliability Council of Texas, Inc.</p>
  </footer>
</body>
</html>
"""


def _eia(title, body, host, path, year, clock, extra) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} | U.S. Energy Information Administration</title>
  <link rel="canonical" href="https://www.eia.gov{path}">
</head>
<body>
  <header>
    <p><a href="https://www.eia.gov/">U.S. Energy Information Administration</a></p>
    <nav>
      <a href="https://www.eia.gov/petroleum/">Petroleum</a>
      <a href="https://www.eia.gov/petroleum/supply/weekly/">Weekly Petroleum Status Report</a>
    </nav>
  </header>
  <main>
    <h1>{title}</h1>
    {body}
  </main>
  <footer>
    <p>U.S. Energy Information Administration &middot; Independent Statistics and Analysis</p>
  </footer>
</body>
</html>
"""


def _aws(title, body, host, path, year, clock, extra) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} | AWS Service Health Dashboard</title>
  <link rel="canonical" href="https://status.aws.amazon.com{path}">
</head>
<body>
  <header>
    <p><a href="https://status.aws.amazon.com/">AWS Service Health Dashboard</a></p>
    <nav>
      <a href="https://status.aws.amazon.com/">Current status</a>
      <a href="https://health.aws.amazon.com/health/status">AWS Health</a>
    </nav>
  </header>
  <main>
    <h1>{title}</h1>
    {body}
  </main>
  <footer>
    <p>Amazon Web Services &middot; Service Health</p>
  </footer>
</body>
</html>
"""


def _generic_official(title, body, host, path, year, clock, extra) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <link rel="canonical" href="https://{host}{path}">
</head>
<body>
  <header><strong>{host}</strong></header>
  <main>
    <h1>{title}</h1>
    {body}
  </main>
  <footer>&copy; {year} {host}</footer>
</body>
</html>
"""


def _plain(title, body, host, path, year, clock, extra) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<h1>{title}</h1>
{body}
</body>
</html>
"""
