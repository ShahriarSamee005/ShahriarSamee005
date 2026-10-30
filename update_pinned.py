#!/usr/bin/env python3
"""
Refresh the Featured Projects section of README.md from the user's
PINNED repositories (GitHub GraphQL `pinnedItems`).

- Order follows the pin order on your profile.
- Pin / unpin a repo and the section updates on the next run.
- No manual editing: content is written between the PINNED markers.

Env:
  GH_TOKEN  GitHub token (the Action passes the built-in GITHUB_TOKEN).
"""
import json
import os
import re
import urllib.request

USERNAME = "shahriarsamee"            # <- your GitHub username
README = "README.md"
START = "<!-- PINNED:START -->"
END = "<!-- PINNED:END -->"
MAX_PINS = 6
CARD_WIDTH = 390                      # px per card; 2 cards per row

# Navy / cyber-blue theme for the github-readme-stats pin cards (hex, no '#')
CARD_PARAMS = (
    "bg_color=081A2E"
    "&title_color=4DB8FF"
    "&text_color=E6F3FF"
    "&icon_color=1689FF"
    "&border_color=0B5FA5"
    "&hide_border=false"
)

QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          nameWithOwner
        }
      }
    }
  }
}
"""


def fetch_pinned():
    token = os.environ["GH_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "pinned-readme-updater",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["pinnedItems"]["nodes"][:MAX_PINS]


def build_block(nodes):
    if not nodes:
        return '<div align="center">\n\n<em>No pinned repositories found.</em>\n\n</div>'
    cards = []
    for n in nodes:
        owner, repo = n["nameWithOwner"].split("/", 1)
        img = (
            f"https://github-readme-stats.vercel.app/api/pin/"
            f"?username={owner}&repo={repo}&{CARD_PARAMS}"
        )
        cards.append(
            f'<a href="https://github.com/{owner}/{repo}">'
            f'<img src="{img}" width="{CARD_WIDTH}" alt="{repo}"/></a>'
        )
    rows = ["".join(cards[i:i + 2]) for i in range(0, len(cards), 2)]
    return '<div align="center">\n\n' + "\n\n".join(rows) + "\n\n</div>"


def main():
    nodes = fetch_pinned()
    block = build_block(nodes)
    with open(README, encoding="utf-8") as f:
        content = f.read()
    pattern = re.escape(START) + r".*?" + re.escape(END)
    replacement = START + "\n" + block + "\n" + END
    new = re.sub(pattern, replacement, content, flags=re.S)
    if new != content:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"Updated Featured Projects with {len(nodes)} pinned repo(s).")
    else:
        print("No change.")


if __name__ == "__main__":
    main()
