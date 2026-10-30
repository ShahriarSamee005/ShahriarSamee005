#!/usr/bin/env python3
"""Update the README Featured Projects block from GitHub profile pins.

The GitHub GraphQL pinnedItems connection preserves the order shown on the
profile. The script renders up to six repositories as a two-column HTML table.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

USERNAME = "shahriarsamee"
README = Path("README.md")
START = "<!-- PINNED:START -->"
END = "<!-- PINNED:END -->"
MAX_PINS = 6

QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          nameWithOwner
          url
          description
          stargazerCount
          primaryLanguage { name }
          isPrivate
        }
      }
    }
  }
}
"""


def fetch_pinned() -> list[dict]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Missing GH_TOKEN or GITHUB_TOKEN environment variable.")

    payload = json.dumps({
        "query": QUERY,
        "variables": {"login": USERNAME},
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "shahriar-pinned-readme-updater",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API returned HTTP {exc.code}: {detail}") from exc

    if result.get("errors"):
        raise SystemExit(f"GitHub GraphQL error: {result['errors']}")

    user = result.get("data", {}).get("user")
    if user is None:
        raise SystemExit(f"GitHub user '{USERNAME}' was not found.")

    return user["pinnedItems"]["nodes"][:MAX_PINS]


def badge(label: str, message: str, logo: str = "") -> str:
    # Shields query strings are URL-encoded by quote() to avoid malformed URLs.
    from urllib.parse import quote

    text = f"{label}-{message}".replace("-", "--").replace("_", "__").replace(" ", "_")
    logo_part = f"&logo={quote(logo)}&logoColor=4DB8FF" if logo else ""
    url = (
        "https://img.shields.io/badge/"
        f"{quote(text, safe='')}"
        f"?style=flat-square&labelColor=050B14&color=0B5FA5"
        f"{logo_part}"
    )
    return f'<img src="{url}" alt="{html.escape(label + " " + message)}"/>'


def render_card(repo: dict) -> str:
    name = html.escape(repo["name"])
    url = html.escape(repo["url"], quote=True)
    description = html.escape(repo.get("description") or "No description provided.")
    language = repo.get("primaryLanguage")
    language_name = language["name"] if language else "Not specified"
    stars = repo.get("stargazerCount", 0)

    metadata = " &nbsp; ".join([
        badge("LANGUAGE", language_name),
        badge("STARS", str(stars), "github"),
        badge("VISIBILITY", "PRIVATE" if repo.get("isPrivate") else "PUBLIC"),
    ])

    return (
        '<td width="50%" valign="top">'
        f'<h3><a href="{url}">{name}</a></h3>'
        f'<p>{description}</p>'
        f'<p>{metadata}</p>'
        f'<p><a href="{url}"><sub>View repository ↗</sub></a></p>'
        '</td>'
    )


def build_block(repositories: list[dict]) -> str:
    if not repositories:
        return (
            '<div align="center">'
            '<sub>No pinned repositories found. Pin repositories on your GitHub profile '
            'and this section will update automatically.</sub>'
            '</div>'
        )

    rows: list[str] = []
    for index in range(0, len(repositories), 2):
        cells = [render_card(repo) for repo in repositories[index:index + 2]]
        if len(cells) == 1:
            cells.append('<td width="50%"></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<table>\n'
        + "\n".join(rows)
        + '\n</table>'
        + '\n<p align="right"><sub>Synced from GitHub pinned repositories</sub></p>'
    )


def main() -> None:
    if not README.exists():
        raise SystemExit(f"{README} not found. Run this script from the repository root.")

    content = README.read_text(encoding="utf-8")
    if START not in content or END not in content:
        raise SystemExit("README is missing the PINNED:START / PINNED:END markers.")

    repositories = fetch_pinned()
    replacement = f"{START}\n{build_block(repositories)}\n{END}"
    pattern = re.escape(START) + r".*?" + re.escape(END)
    updated, count = re.subn(pattern, lambda _: replacement, content, count=1, flags=re.S)

    if count != 1:
        raise SystemExit("Could not locate exactly one pinned-project block.")

    if updated != content:
        README.write_text(updated, encoding="utf-8")
        print(f"Updated Featured Projects with {len(repositories)} pinned repositories.")
    else:
        print("Featured Projects are already up to date.")


if __name__ == "__main__":
    main()
