"""Step-by-step copy for obtaining an iRacing OAuth access token."""

from __future__ import annotations

OAUTH_REGISTRATION_PAUSED_HTML = (
    "<b>iRacing has paused new OAuth client registrations.</b> "
    "They are evaluating third-party API and SDK usage; when sign-ups reopen, "
    "iRacing will announce it on their forums and in release notes.<br><br>"
    "<b>What you can do today:</b><br>"
    "• Use <b>Import race JSON…</b> on the main screen (iRacing event_result export) — "
    "this does not need OAuth.<br>"
    "• If you already registered an OAuth app before the pause, you can still use "
    "the steps below with your existing Client ID.<br>"
    "• Live session scouting (Windows SDK) still works without the Data API."
)

# (section title, HTML body)
OAUTH_TOKEN_GUIDE_SECTIONS: list[tuple[str, str]] = [
    (
        "Current status — new OAuth apps on hold",
        OAUTH_REGISTRATION_PAUSED_HTML,
    ),
    (
        "Step 1 — Register an OAuth client with iRacing (when available)",
        (
            "When registration reopens, request a <b>Client ID</b>, "
            "<b>Client Secret</b> (if your client type receives one), "
            "and at least one <b>Redirect URI</b> — for local testing, "
            "<code>http://localhost:8080/callback</code> is common.<br><br>"
            "Official guide: "
            '<a href="https://oauth.iracing.com/oauth2/book/introduction.html">'
            "oauth.iracing.com — Introduction</a> · "
            '<a href="https://forums.iracing.com/">iRacing forums</a> for announcements.'
        ),
    ),
    (
        "Step 2 — Open the authorize URL in your browser",
        (
            "Send your browser to iRacing’s authorize endpoint (replace placeholders "
            "with your registered values):<br><br>"
            "<code>https://oauth.iracing.com/oauth2/authorize"
            "?client_id=YOUR_CLIENT_ID"
            "&amp;redirect_uri=YOUR_URL_ENCODED_REDIRECT_URI"
            "&amp;response_type=code"
            "&amp;scope=iracing.auth"
            "&amp;state=any_random_string"
            "&amp;code_challenge=PKCE_CHALLENGE"
            "&amp;code_challenge_method=S256</code><br><br>"
            "PKCE is required or strongly recommended — see "
            '<a href="https://oauth.iracing.com/oauth2/book/authorize_endpoint.html">'
            "/authorize documentation</a>. "
            "Sign in with your iRacing account when prompted."
        ),
    ),
    (
        "Step 3 — Copy the authorization code",
        (
            "After you approve access, the browser redirects to your Redirect URI with "
            "query parameters, for example:<br><br>"
            "<code>https://localhost:8080/callback?code=…&amp;state=…</code><br><br>"
            "Copy the <b>code</b> value from the address bar (everything after "
            "<code>code=</code> up to the next <code>&amp;</code>). "
            "Verify the <code>state</code> matches what you sent."
        ),
    ),
    (
        "Step 4 — Exchange the code for tokens",
        (
            "POST to the token endpoint (form-urlencoded body):<br><br>"
            "<code>POST https://oauth.iracing.com/oauth2/token</code><br><br>"
            "Fields: <code>grant_type=authorization_code</code>, "
            "<code>client_id</code>, <code>client_secret</code> (if issued), "
            "<code>code</code>, <code>redirect_uri</code> (must match Step 2), "
            "and <code>code_verifier</code> if you used PKCE.<br><br>"
            "The JSON response includes <code>access_token</code> and often "
            "<code>refresh_token</code>. Details: "
            '<a href="https://oauth.iracing.com/oauth2/book/token_endpoint.html">'
            "/token documentation</a>."
        ),
    ),
    (
        "Step 5 — Paste the token into GridNotes",
        (
            "Copy the <b>access_token</b> string from the JSON response (not the "
            "refresh token). Paste it into the <b>OAuth access token</b> field above, "
            "click <b>Test connection</b>, then <b>Save settings</b>."
        ),
    ),
    (
        "Step 6 — Refresh when the token expires",
        (
            "Access tokens are short-lived (often about 10 minutes). When auto-fetch or "
            "Test connection fails, exchange your <code>refresh_token</code> for a new "
            "access token using <code>grant_type=refresh_token</code> at the same "
            "/token endpoint, then update the field here.<br><br>"
            "Refresh tokens are single-use — each refresh returns a new refresh token."
        ),
    ),
]


def combined_oauth_guide_html() -> str:
    """Single HTML block for a collapsed in-app guide."""
    blocks: list[str] = []
    for title, body in OAUTH_TOKEN_GUIDE_SECTIONS:
        blocks.append(f"<p><b>{title}</b><br>{body}</p>")
    return "".join(blocks)


def oauth_registration_paused_plain() -> str:
    """Short notice for labels (no HTML)."""
    return (
        "iRacing has paused new OAuth client registrations. Use Import race JSON on "
        "the main screen for now, or use an existing OAuth app if you already have one."
    )
