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
        "forum": _forum,
        "google": _google,
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


def _forum(title, body, host, path, year, clock, extra) -> str:
    author = extra.get("author", "anon_user")
    posted = extra.get("posted", clock.strftime("%Y-%m-%d %H:%M UTC"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title} — python-dev forum</title>
  <meta name="robots" content="index,follow">
</head>
<body>
  <header>
    <strong>python-dev forum</strong>
    <span>unofficial community thread</span>
  </header>
  <article>
    <h1>{title}</h1>
    <p class="meta">Posted by {author} on {posted} &middot; 3 replies</p>
    <div class="post">{body}</div>
  </article>
  <aside>
    <p>This is an unofficial community forum. Claims here are not endorsed by the Python Software Foundation.</p>
  </aside>
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
