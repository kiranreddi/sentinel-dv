"""Vercel Python entrypoint for lightweight health checks."""


def app(environ, start_response):
    """WSGI app used by Vercel's Python runtime."""
    body = (
        b"Sentinel DV is an MCP server package. "
        b"Use sentinel-dv-server for stdio-based execution."
    )
    headers = [
        ("Content-Type", "text/plain; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    start_response("200 OK", headers)
    return [body]
