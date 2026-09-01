#!/usr/bin/env bash
# Prepares this directory for a first push to GitHub.
#
# It does NOT push. It initialises the repository, substitutes your username
# into the placeholder links, and prints the two commands you run yourself.
# Pushing needs your credentials, which belong to you and not to a script you
# did not write.
set -euo pipefail

USER="${1:-}"
REPO="${2:-nepal-cryosphere-inventory}"

if [[ -z "$USER" ]]; then
  echo "usage: ./setup-github.sh YOUR-GITHUB-USERNAME [repo-name]" >&2
  exit 1
fi

echo "==> Substituting YOUR-USERNAME -> $USER"
for f in README.md pyproject.toml; do
  [[ -f "$f" ]] && sed -i.bak "s|YOUR-USERNAME|$USER|g; s|nepal-cryosphere-inventory|$REPO|g" "$f" && rm -f "$f.bak"
done

echo "==> Checking for files over 50 MB"
big=$(find . -type f -size +50M -not -path './.git/*' || true)
if [[ -n "$big" ]]; then
  echo "    WARNING, these exceed GitHub's 50 MB advisory limit:"
  echo "$big" | sed 's/^/      /'
  echo "    Consider adding them to .gitignore and attaching to a Release."
else
  echo "    none"
fi

echo "==> Sizes"
du -sh data docs nepal_glaciers 2>/dev/null | sed 's/^/    /'
echo "    total: $(du -sh . | cut -f1)"

if [[ ! -d .git ]]; then
  echo "==> git init"
  git init -q
  git branch -M main
fi

git add -A
echo
echo "==> Staged $(git diff --cached --numstat | wc -l) files. Nothing has been pushed."
echo
echo "Run these yourself:"
echo
echo "  git commit -m 'Nepal cryosphere inventory v1.0.0'"
echo "  git remote add origin https://github.com/$USER/$REPO.git"
echo "  git push -u origin main"
echo
echo "Then: Settings -> Pages -> Source: GitHub Actions."
echo "The site will be at https://$USER.github.io/$REPO/"
