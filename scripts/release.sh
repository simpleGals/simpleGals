#!/opt/homebrew/bin/bash
#
# SPDX-FileCopyrightText: 2026 Tim Case <tim@lnx.cx>
# SPDX-License-Identifier: MIT
#
# simpleGals release helper.
#
# Shows what is already published, asks you for the next version, then does the
# mechanical parts in the one order that publish.yml accepts:
#
#   VERSION written -> committed -> tag signed on THAT commit -> commit and tag pushed
#
# publish.yml checks out the *tag* and compares the tag name to `cat VERSION`.
# If the bump is not in the commit the tag points at, the release fails. That is
# the whole reason this script exists.
#
# It stops after pushing the tag and prints the `gh release create` command.
# Creating the release is what actually triggers the PyPI publish, and that step
# is yours to run.

set -euo pipefail
unset CDPATH

REPO="simpleGals/simpleGals"
PKG="simplegals"
BRANCH="main"

cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
    cat <<'USAGE'
Usage: scripts/release.sh [-h|--help]

Cuts a simpleGals release in the one order publish.yml accepts:

  VERSION written -> committed -> tag signed on that commit -> both pushed

Prompts for the next version and a one-line release message, builds the
artifacts, shows you exactly what will be pushed, and asks before pushing
anything. Stops after the tag and prints the `gh release create` command,
which is what actually triggers the PyPI upload.

Nothing is pushed until you answer the "Proceed?" prompt. Any exit before
that point restores VERSION.
USAGE
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    "") ;;
    *) printf 'unknown argument: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
esac

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
info() { printf '  %s\n' "$*"; }
warn() { printf '\033[33m!! %s\033[0m\n' "$*"; }
die()  { printf '\033[31mxx %s\033[0m\n' "$*" >&2; exit 1; }

trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    printf '%s' "$s"
}

# ---------------------------------------------------------------- pre-flight

for tool in gh gpg git make python3; do
    command -v "$tool" >/dev/null || die "$tool is not installed"
done

[ -f VERSION ] || die "no VERSION file; are you in the repo root?"

git fetch --quiet --tags origin

current_branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$current_branch" = "$BRANCH" ] || die "on '$current_branch', releases are cut from '$BRANCH'"

[ -z "$(git status --porcelain)" ] || die "working tree is dirty; commit or stash first"

local_head="$(git rev-parse HEAD)"
remote_head="$(git rev-parse "origin/$BRANCH")"
[ "$local_head" = "$remote_head" ] || die "$BRANCH has diverged from origin/$BRANCH; pull or push first"

# ---------------------------------------------------------------- what exists

bold "Published on PyPI"
if pypi_json="$(curl -fsS "https://pypi.org/pypi/$PKG/json" 2>/dev/null)"; then
    printf '%s' "$pypi_json" | python3 -c '
import json, sys
data = json.load(sys.stdin)
rels = [(v[0]["upload_time"], k) for k, v in data["releases"].items() if v]
for when, ver in sorted(rels, reverse=True)[:2]:
    print(f"  {ver:<10} {when[:10]}")
' || warn "could not parse the PyPI response"
else
    warn "could not reach PyPI (first release, or network is down)"
fi

bold "Released on GitHub"
gh release list --repo "$REPO" --limit 2 \
    --json tagName,publishedAt \
    --jq '.[] | "  \(.tagName | . + " " * (10 - length)) \(.publishedAt[:10])"' \
    || warn "could not list GitHub releases"

version_now="$(cat VERSION)"
bold "VERSION file"
info "$version_now"
echo

# ---------------------------------------------------------------- gpg warm-up

# gpg needs a tty to drive pinentry-curses. Without GPG_TTY it dies with
# "Inappropriate ioctl for device" - at the tag step, after the branch has
# already been pushed. Set it here, once, for both the probe and the real
# signature.
if [ -z "${GPG_TTY:-}" ] && tty_dev="$(tty 2>/dev/null)"; then
    export GPG_TTY="$tty_dev"
fi
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1 || true

# `gpg-agent is running` says nothing about whether the key is cached. Actually
# sign a byte and see. --pinentry-mode error makes it fail instead of prompting,
# which is exactly the signal we want: fail here means you get asked later.
signing_key="$(git config --get user.signingkey || true)"
gpg_args=(--batch --pinentry-mode error --sign --output /dev/null)
[ -n "$signing_key" ] && gpg_args=(--local-user "$signing_key" "${gpg_args[@]}")

if printf 'x' | gpg "${gpg_args[@]}" - 2>/dev/null; then
    info "gpg key is cached, signing will not prompt"
else
    warn "gpg key is NOT cached - have your passphrase ready, you will be asked at the tag step"
fi
echo

# ---------------------------------------------------------------- ask

read -r -p "Next version: " version_raw || die "aborted"
version_new="$(trim "$version_raw")"

[ -n "$version_new" ] || die "no version given"

[[ "$version_new" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || die "'$version_new' is not X.Y.Z"

git rev-parse -q --verify "refs/tags/$version_new" >/dev/null \
    && die "tag $version_new already exists"

if [ -n "${pypi_json:-}" ] \
   && printf '%s' "$pypi_json" | python3 -c '
import json, sys
sys.exit(0 if sys.argv[1] in json.load(sys.stdin)["releases"] else 1)
' "$version_new"; then
    die "$version_new is already on PyPI; versions there are immutable, pick another"
fi

read -r -p "Release message: " message_raw || die "aborted"
message="$(trim "$message_raw")"
[ -n "$message" ] || die "no release message given"

echo

# ---------------------------------------------------------------- build

# Any exit between writing VERSION and committing it - build failure, Ctrl-C,
# EOF on a prompt, answering no - has to put the file back.
#
# Once the commit exists but before anything is pushed there is a second thing
# to undo: the commit itself. Leaving it behind makes the next run die on
# "diverged from origin", which is a confusing way to report "the tag step
# failed". Only ever unwind a commit this run created.
version_written=0
committed=0
pushed=0
head_before=""
cleanup() {
    local rc=$?
    if [ "$version_written" -eq 1 ] && [ "$committed" -eq 0 ]; then
        git checkout -- VERSION 2>/dev/null || true
        warn "VERSION restored to $version_now, nothing committed"
    fi
    if [ "$committed" -eq 1 ] && [ "$pushed" -eq 0 ] && [ -n "$head_before" ]; then
        git tag -d "$version_new" >/dev/null 2>&1 || true
        git reset --hard "$head_before" >/dev/null 2>&1 || true
        warn "rolled back to $(git rev-parse --short "$head_before"), nothing pushed"
    fi
    exit "$rc"
}
trap cleanup EXIT INT TERM

# VERSION carries no trailing newline; printf keeps it that way.
if [ "$version_new" != "$version_now" ]; then
    printf '%s' "$version_new" > VERSION
    version_written=1
    info "VERSION: $version_now -> $version_new"
else
    info "VERSION already reads $version_new, leaving it alone"
fi

bold "Building"
make build || die "build failed"

# A green build proves the syntax. It does not prove hatchling read the new
# VERSION - check the artifact names for that.
wheel="dist/${PKG}-${version_new}-py3-none-any.whl"
sdist="dist/${PKG}-${version_new}.tar.gz"
for artifact in "$wheel" "$sdist"; do
    [ -f "$artifact" ] \
        || die "expected $artifact, not found. Built: $(ls dist/ 2>/dev/null | tr '\n' ' ')"
done
info "built $(basename "$wheel")"
info "built $(basename "$sdist")"
echo

# ---------------------------------------------------------------- confirm

bold "About to push"
info "commit  release: bump VERSION to $version_new"
info "tag     $version_new (signed) on that commit"
info "remote  $REPO"
echo
read -r -p "Proceed? [y/N] " confirm || die "aborted"
case "$(trim "$confirm")" in
    y|Y|yes|Yes) ;;
    *) die "aborted, nothing pushed" ;;
esac
echo

# ---------------------------------------------------------------- commit, tag

if ! git diff --quiet -- VERSION; then
    head_before="$(git rev-parse HEAD)"
    git add VERSION
    git commit -m "release: bump VERSION to $version_new"
    committed=1
fi

# Sign first, push second. Signing is the step that can still fail (locked key,
# no tty, wrong passphrase) and it is purely local, so a failure here leaves the
# remote untouched instead of stranding a pushed commit that no tag points at.
#
# Bare version as the tag message, matching 0.1.2 through 0.4.0. The prose goes
# in the release body, not here.
git tag -s "$version_new" -m "$version_new" \
    || die "tag signing failed; nothing was pushed. Fix gpg, then re-run."

git push origin "$BRANCH"
git push origin "$version_new"
pushed=1

echo
bold "Tag $version_new pushed and signed."
echo
info "Verify GitHub accepted the signature:"
printf '\n    gh api /repos/%s/git/tags/$(gh api /repos/%s/git/ref/tags/%s --jq .object.sha) --jq .verification\n\n' \
    "$REPO" "$REPO" "$version_new"
info "Then publish (this triggers the PyPI upload):"
printf '\n    gh release create %s --repo %s --title %s --notes %s\n\n' \
    "$version_new" "$REPO" "$(printf '%q' "$version_new")" "$(printf '%q' "$message")"
