#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "${repo_root}"

if [[ ! -d .git ]]; then
    printf 'No .git directory found; skipping local git hook installation.\n' >&2
    exit 0
fi

mkdir -p .git/hooks
# Keep inherited guards active when enabling repository-specific hooks.
inherited_hooks=$(git config --path --get core.hooksPath || true)
if [[ -n $inherited_hooks && $inherited_hooks != .git/hooks ]]; then
    for inherited in "$inherited_hooks"/*; do
        [[ -f $inherited && -x $inherited ]] || continue
        name=$(basename "$inherited")
        case $name in
            pre-commit|commit-msg) cp -L "$inherited" ".git/hooks/$name.inherited" ;;
            *)
                if [[ -e .git/hooks/$name ]] && ! cmp -s "$inherited" ".git/hooks/$name"; then
                    echo "Existing $name hook needs manual reconciliation" >&2
                    exit 1
                fi
                cp -L "$inherited" ".git/hooks/$name"
                ;;
        esac
        chmod +x .git/hooks/"$name"* 2>/dev/null || true
    done
fi
git config --local core.hooksPath .git/hooks

existing_hook=.git/hooks/pre-commit
chained_hook=.git/hooks/pre-commit.local

if [[ -f "${existing_hook}" ]] && ! grep -q 'AI_FILE_GUARD_BEGIN' "${existing_hook}"; then
    cp "${existing_hook}" "${chained_hook}"
    chmod +x "${chained_hook}"
fi

cat > "${existing_hook}" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

# AI_FILE_GUARD_BEGIN
blocked=$(
  git diff --cached --name-only --diff-filter=ACMR |
    grep -E '(^|/)(\.ktask|\.codex|\.claude|\.claude_[^/]*|\.kiro|\.aim|\.cursor|\.copilot|\.continue|\.windsurf|\.chat_history|\.ai|\.agent)(/|$)|(^|/)(\.aider[^/]*|.*\.prompt|.*\.prompt\.md|.*\.context|.*\.context\.md)(/|$)' || true
)

if [[ -n "${blocked}" ]]; then
  echo "Refusing to commit AI/task-runner files, prompts, context, or chat logs:" >&2
  echo "${blocked}" >&2
  echo >&2
  echo "Remove them from the index with: git restore --staged <file>" >&2
  exit 1
fi
# AI_FILE_GUARD_END
expected='Illya Yalovyy <1623643+IllyaYalovyy@users.noreply.github.com>'
identity=$(git var GIT_AUTHOR_IDENT)
if [[ ${identity%>*} != "${expected%>}" ]]; then
    echo "Commit author must be $expected" >&2
    exit 1
fi
./scripts/check-version.py --staged

if [[ -x .git/hooks/pre-commit.inherited ]]; then
    .git/hooks/pre-commit.inherited "$@"
fi
if [[ -x .git/hooks/pre-commit.local ]]; then
  .git/hooks/pre-commit.local "$@"
fi
HOOK

chmod +x "${existing_hook}"
printf 'Installed local AI-file pre-commit guard at %s.\n' "${existing_hook}"

if [[ -f .git/hooks/commit-msg ]] && ! grep -q 'SINGLE_AUTHOR_GUARD' .git/hooks/commit-msg; then
    cp .git/hooks/commit-msg .git/hooks/commit-msg.local
fi
cat > .git/hooks/commit-msg <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail
# SINGLE_AUTHOR_GUARD
if grep -qiE '^[[:space:]]*Co-authored-by[[:space:]]*:' "$1"; then
    echo 'Co-authored-by trailers are not allowed.' >&2
    exit 1
fi
if [[ -x .git/hooks/commit-msg.inherited ]]; then
    .git/hooks/commit-msg.inherited "$@"
fi
if [[ -x .git/hooks/commit-msg.local ]]; then
    .git/hooks/commit-msg.local "$@"
fi
HOOK
chmod +x .git/hooks/commit-msg
