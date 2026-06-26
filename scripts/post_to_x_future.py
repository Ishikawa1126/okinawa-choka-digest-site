"""
Future extension point for X auto posting.

This project intentionally does not auto-post to X at first.
When you decide to use the paid X API, add these GitHub Secrets:

- X_API_KEY
- X_API_SECRET
- X_ACCESS_TOKEN
- X_ACCESS_TOKEN_SECRET

Then this script can be expanded to read the latest generated Markdown,
extract the "X投稿用テキスト" code block, and post it via the X API.
"""

from __future__ import annotations


def main() -> None:
    print("X auto-posting is intentionally disabled. Configure X API secrets before enabling it.")


if __name__ == "__main__":
    main()

