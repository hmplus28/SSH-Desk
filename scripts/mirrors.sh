#!/usr/bin/env bash
# SSH Desk - shared PyPI mirror-fallback helpers.
#
# Sourced by: install.sh, build.sh, download_wheels.sh
#
# Why: PyPI and GitHub are unreachable or throttled in some networks and
# during outages. Every pip invocation goes through `pip_resilient`, which:
#   1. installs from a local wheelhouse when one is configured (offline mode),
#   2. uses one forced mirror when SSH_DESK_PIP_INDEX_URL is set,
#   3. otherwise walks a fallback chain of mirrors until one succeeds.
#
# Environment overrides:
#   SSH_DESK_PIP_INDEX_URL   force one index URL (no fallback chain)
#   SSH_DESK_MIRRORS         replace the whole chain: "url1 url2 url3"
#   SSH_DESK_WHEELHOUSE      dir with pre-downloaded wheels -> offline mode
#   SSH_DESK_PIP_TIMEOUT     per-request socket timeout, seconds (default 20)
#   SSH_DESK_PIP_RETRIES     pip retries per mirror        (default 1)
#   SSH_DESK_PIP             pip invocation prefix (array). Default: python3 -m pip

# Mirror chain — tried in order, first success wins.
# An unreachable mirror costs one timeout, then is skipped automatically.
SSH_DESK_DEFAULT_MIRRORS=(
    "https://pypi.org/simple"                        # official (global)
    "https://mirror.arvancloud.ir/pypi/simple"       # Iran (ArvanCloud)
    "https://pypi.tuna.tsinghua.edu.cn/simple"       # China (TUNA)
    "https://mirrors.aliyun.com/pypi/simple"         # China (Aliyun)
    "https://mirrors.cloud.tencent.com/pypi/simple"  # China (Tencent)
)

ssh_desk_log()  { printf '\033[1;34m::\033[0m %s\n' "$*"; }
ssh_desk_warn() { printf '\033[1;33m::\033[0m %s\n' "$*"; }
ssh_desk_err()  { printf '\033[1;31m✘\033[0m %s\n' "$*" >&2; }

# name -> index URL  (used by --mirror-name)
# names: pypi | ir | tuna | aliyun | tencent
ssh_desk_mirror_url() {
    case "${1:-}" in
        pypi|official)      printf '%s\n' "https://pypi.org/simple" ;;
        ir|iran|arvan)      printf '%s\n' "https://mirror.arvancloud.ir/pypi/simple" ;;
        tuna|tsinghua)      printf '%s\n' "https://pypi.tuna.tsinghua.edu.cn/simple" ;;
        aliyun)             printf '%s\n' "https://mirrors.aliyun.com/pypi/simple" ;;
        tencent|qq)         printf '%s\n' "https://mirrors.cloud.tencent.com/pypi/simple" ;;
        *) ssh_desk_err "unknown mirror name: '$1' (pypi|ir|tuna|aliyun|tencent)"; return 1 ;;
    esac
}

# active chain: env override (array or space-separated URLs) wins over built-ins
ssh_desk_mirrors() {
    local decl
    if decl="$(declare -p SSH_DESK_MIRRORS 2>/dev/null)"; then
        if [[ "$decl" == *"declare -a"* ]]; then
            SSH_DESK_ACTIVE_MIRRORS=("${SSH_DESK_MIRRORS[@]}")
        else
            # shellcheck disable=SC2206  # intentional word splitting on purpose
            SSH_DESK_ACTIVE_MIRRORS=($SSH_DESK_MIRRORS)
        fi
    else
        SSH_DESK_ACTIVE_MIRRORS=("${SSH_DESK_DEFAULT_MIRRORS[@]}")
    fi
}

# pip_resilient <install|download> [pip args...]
# Runs "$SSH_DESK_PIP" <subcmd> [args] against the wheelhouse / forced mirror /
# fallback chain. Caller sets SSH_DESK_PIP as an array, e.g.:
#   SSH_DESK_PIP=("$VENV_DIR/bin/pip") pip_resilient install "$REPO_DIR"
pip_resilient() {
    local sub="${1:-}"; [ -n "$sub" ] || { ssh_desk_err "pip_resilient: subcommand required"; return 2; }
    shift
    # pip invocation: SSH_DESK_PIP array if declared, else system "python3 -m pip"
    local pip_cmd
    if declare -p SSH_DESK_PIP >/dev/null 2>&1; then
        pip_cmd=("${SSH_DESK_PIP[@]}")
    else
        pip_cmd=(python3 -m pip)
    fi
    local timeout="${SSH_DESK_PIP_TIMEOUT:-20}"
    local retries="${SSH_DESK_PIP_RETRIES:-1}"
    local wheelhouse="${SSH_DESK_WHEELHOUSE:-}"

    # 1) offline mode: install strictly from local wheels
    if [ -n "$wheelhouse" ]; then
        if [ "$sub" != "install" ]; then
            ssh_desk_warn "wheelhouse is set but subcommand is '$sub' — running online"
        else
            if [ ! -d "$wheelhouse" ]; then
                ssh_desk_err "wheelhouse not found: $wheelhouse"
                printf '  Fill it first:  bash scripts/download_wheels.sh\n' >&2
                return 1
            fi
            ssh_desk_log "offline install (no network) from: $wheelhouse"
            "${pip_cmd[@]}" install --no-index --find-links "$wheelhouse" "$@"
            return $?
        fi
    fi

    # 2) forced single mirror
    if [ -n "${SSH_DESK_PIP_INDEX_URL:-}" ]; then
        ssh_desk_log "pip $sub via forced mirror: $SSH_DESK_PIP_INDEX_URL"
        "${pip_cmd[@]}" "$sub" --index-url "$SSH_DESK_PIP_INDEX_URL" \
            --timeout "$timeout" --retries "$retries" "$@"
        return $?
    fi

    # 3) fallback chain
    local m
    ssh_desk_mirrors
    for m in "${SSH_DESK_ACTIVE_MIRRORS[@]}"; do
        ssh_desk_log "pip $sub trying mirror: $m"
        if "${pip_cmd[@]}" "$sub" --index-url "$m" \
                --timeout "$timeout" --retries "$retries" "$@"; then
            ssh_desk_log "pip $sub OK via $m"
            return 0
        fi
        ssh_desk_warn "mirror failed, trying next: $m"
    done

    ssh_desk_err "all mirrors failed — check your connection."
    printf '  Pre-download wheels once (on any network), then install offline:\n' >&2
    printf '    bash scripts/download_wheels.sh --mirror-name ir\n' >&2
    printf '    bash scripts/install.sh --offline\n' >&2
    return 1
}
