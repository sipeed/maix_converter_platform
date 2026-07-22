#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PULSAR2_IMAGE="${PULSAR2_IMAGE:-pulsar2:6.0}"
PULSAR2_URL="${PULSAR2_URL:-https://huggingface.co/AXERA-TECH/Pulsar2/resolve/main/6.0/ax_pulsar2_6.0.tar.gz}"
TPUC_DEV_IMAGE_V34="${TPUC_DEV_IMAGE_V34:-sophgo/tpuc_dev:v3.4}"
TPUC_DEV_IMAGE_LATEST="${TPUC_DEV_IMAGE_LATEST:-sophgo/tpuc_dev:latest}"
TPUC_DEV_URL="${TPUC_DEV_URL:-https://sophon-assets.sophon.cn/sophon-prod-s3/drive/25/04/15/16/tpuc_dev_v3.4.tar.gz}"
TPUMLIR_IMAGE="${TPUMLIR_IMAGE:-maixcam-tpumlir:v3.4}"
DOWNLOADS_DIR="${DOWNLOADS_DIR:-$ROOT_DIR/downloads}"

TARGET=""
PULSAR2_TAR=""
TPUC_DEV_TAR=""
PULSAR2_SOURCE_IMAGE=""
DOWNLOAD_PULSAR2=0
DOWNLOAD_TPUC_DEV=0
FORCE_BUILD=0
SKIP_VERIFY=0
TPUC_BASE_IMAGE=""
INTERACTIVE=0
PROMPT_RESULT=""

usage() {
  cat <<'EOF'
Usage:
  scripts/setup_toolchains.sh
  scripts/setup_toolchains.sh [all|pulsar2|tpumlir] [options]

Targets:
  all                 Prepare both Pulsar2 and TPU-MLIR images.
  pulsar2             Prepare only pulsar2:6.0 for MaixCam2.
  tpumlir             Prepare only maixcam-tpumlir:v3.4 for MaixCAM / MaixCAM Pro.

Options:
  --pulsar2-tar PATH          Load Pulsar2 from a local .tar or .tar.gz image package.
  --pulsar2-source-image IMG  Tag an already loaded Pulsar2 image as pulsar2:6.0.
  --download-pulsar2          Download the Pulsar2 package before docker load.
  --pulsar2-url URL           Override the Pulsar2 package URL.
  --tpuc-dev-tar PATH         Load sophgo/tpuc_dev from a local .tar or .tar.gz image package.
  --download-tpuc-dev         Pull/download the sophgo/tpuc_dev base image if it is missing.
  --tpuc-dev-url URL          Override the sophgo/tpuc_dev package URL.
  --downloads-dir DIR         Directory for downloaded image packages.
  --force-build               Rebuild maixcam-tpumlir:v3.4 even if it already exists.
  --skip-verify               Skip docker run verification commands.
  --interactive               Show guided menus even when a target is provided.
  -h, --help                  Show this help.

Examples:
  scripts/setup_toolchains.sh
  scripts/setup_toolchains.sh pulsar2 --pulsar2-tar ~/Downloads/ax_pulsar2_6.0.tar.gz
  scripts/setup_toolchains.sh tpumlir --download-tpuc-dev
  scripts/setup_toolchains.sh all --download-pulsar2 --download-tpuc-dev

Running without a target opens an interactive menu. In non-interactive shells,
the default target is all. The script does not download multi-GB image packages
unless you choose that in the menu or pass the --download-* flags explicitly.
EOF
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

run() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  "$@"
}

parse_args() {
  if [[ $# -gt 0 ]]; then
    case "$1" in
      all|pulsar2|tpumlir)
        TARGET="$1"
        shift
        ;;
    esac
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --pulsar2-tar)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        PULSAR2_TAR="${2:-}"
        shift 2
        ;;
      --pulsar2-source-image)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        PULSAR2_SOURCE_IMAGE="${2:-}"
        shift 2
        ;;
      --download-pulsar2)
        DOWNLOAD_PULSAR2=1
        shift
        ;;
      --pulsar2-url)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        PULSAR2_URL="${2:-}"
        shift 2
        ;;
      --tpuc-dev-tar)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        TPUC_DEV_TAR="${2:-}"
        shift 2
        ;;
      --download-tpuc-dev)
        DOWNLOAD_TPUC_DEV=1
        shift
        ;;
      --tpuc-dev-url)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        TPUC_DEV_URL="${2:-}"
        shift 2
        ;;
      --downloads-dir)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        DOWNLOADS_DIR="${2:-}"
        shift 2
        ;;
      --force-build)
        FORCE_BUILD=1
        shift
        ;;
      --skip-verify)
        SKIP_VERIFY=1
        shift
        ;;
      --interactive)
        INTERACTIVE=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "unknown argument: $1"
        ;;
    esac
  done
}

prompt_choice() {
  local prompt="$1"
  local answer=""
  shift

  while true; do
    printf '\n%s\n' "$prompt" >&2
    printf '%s\n' "$@" >&2
    printf '> ' >&2
    IFS= read -r answer || die "failed to read input"
    case "$answer" in
      ''|*[!0-9]*)
        printf '请输入数字选项。\n' >&2
        ;;
      *)
        PROMPT_RESULT="$answer"
        return
        ;;
    esac
  done
}

expand_user_path() {
  local input="$1"
  case "$input" in
    "~")
      printf '%s\n' "$HOME"
      ;;
    "~/"*)
      printf '%s/%s\n' "$HOME" "${input#"~/"}"
      ;;
    *)
      printf '%s\n' "$input"
      ;;
  esac
}

prompt_path() {
  local prompt="$1"
  local path=""
  while true; do
    printf '%s\n> ' "$prompt" >&2
    IFS= read -r path || die "failed to read input"
    path="$(expand_user_path "$path")"
    if [[ -f "$path" ]]; then
      PROMPT_RESULT="$path"
      return
    fi
    printf '文件不存在：%s\n' "$path" >&2
  done
}

needs_pulsar2_menu() {
  [[ "$TARGET" == "pulsar2" || "$TARGET" == "all" ]]
}

needs_tpumlir_menu() {
  [[ "$TARGET" == "tpumlir" || "$TARGET" == "all" ]]
}

configure_interactive() {
  if [[ "$INTERACTIVE" -eq 0 && -n "$TARGET" ]]; then
    return
  fi
  if [[ ! -t 0 ]]; then
    [[ -n "$TARGET" ]] || TARGET="all"
    return
  fi

  local choice=""
  if [[ -z "$TARGET" || "$INTERACTIVE" -eq 1 ]]; then
    prompt_choice \
      "请选择要部署的转换环境：" \
      "  1) MaixCAM / MaixCAM Pro（TPU-MLIR，生成 .cvimodel）" \
      "  2) MaixCam2（Pulsar2，生成 .axmodel）" \
      "  3) 两者都部署"
    choice="$PROMPT_RESULT"
    case "$choice" in
      1) TARGET="tpumlir" ;;
      2) TARGET="pulsar2" ;;
      3) TARGET="all" ;;
      *) die "unsupported menu choice: $choice" ;;
    esac
  fi

  if needs_pulsar2_menu && [[ -z "$PULSAR2_TAR" && -z "$PULSAR2_SOURCE_IMAGE" && "$DOWNLOAD_PULSAR2" -eq 0 ]]; then
    prompt_choice \
      "MaixCam2 / Pulsar2 镜像来源：" \
      "  1) 我已有本地 Pulsar2 .tar 或 .tar.gz 镜像包" \
      "  2) 自动下载 Pulsar2 镜像包" \
      "  3) Docker 里已经加载过镜像，只检查/自动 tag"
    choice="$PROMPT_RESULT"
    case "$choice" in
      1)
        prompt_path "请输入 Pulsar2 镜像包路径："
        PULSAR2_TAR="$PROMPT_RESULT"
        ;;
      2) DOWNLOAD_PULSAR2=1 ;;
      3) ;;
      *) die "unsupported menu choice: $choice" ;;
    esac
  fi

  if needs_tpumlir_menu && [[ -z "$TPUC_DEV_TAR" && "$DOWNLOAD_TPUC_DEV" -eq 0 ]]; then
    prompt_choice \
      "MaixCAM / TPU-MLIR 基础镜像来源：" \
      "  1) 我已有本地 sophgo/tpuc_dev .tar 或 .tar.gz 镜像包" \
      "  2) 自动 pull sophgo/tpuc_dev，失败后下载镜像包" \
      "  3) Docker 里已经有 sophgo/tpuc_dev，只检查并构建派生镜像"
    choice="$PROMPT_RESULT"
    case "$choice" in
      1)
        prompt_path "请输入 sophgo/tpuc_dev 镜像包路径："
        TPUC_DEV_TAR="$PROMPT_RESULT"
        ;;
      2) DOWNLOAD_TPUC_DEV=1 ;;
      3) ;;
      *) die "unsupported menu choice: $choice" ;;
    esac
  fi
}

require_value() {
  local value="$1"
  local option="$2"
  [[ -n "$value" ]] || die "$option requires a value"
}

check_args() {
  require_value "$PULSAR2_IMAGE" "PULSAR2_IMAGE"
  require_value "$TPUMLIR_IMAGE" "TPUMLIR_IMAGE"
  require_value "$DOWNLOADS_DIR" "--downloads-dir"

  if [[ -n "$PULSAR2_TAR" && ! -f "$PULSAR2_TAR" ]]; then
    die "Pulsar2 package not found: $PULSAR2_TAR"
  fi
  if [[ -n "$TPUC_DEV_TAR" && ! -f "$TPUC_DEV_TAR" ]]; then
    die "sophgo/tpuc_dev package not found: $TPUC_DEV_TAR"
  fi
}

check_docker() {
  log "Checking Docker"
  command -v docker >/dev/null 2>&1 || die "docker command not found. Install Docker first."
  run docker --version

  if ! docker info >/dev/null 2>&1; then
    cat >&2 <<'EOF'
ERROR: Docker daemon is not reachable by the current user.

On Linux, check that Docker is running and that your user can access it:
  sudo systemctl start docker
  sudo usermod -aG docker $USER

After changing groups, log out and log in again, then rerun this script.
On Windows, start Docker Desktop and make sure WSL2 integration is enabled.
EOF
    exit 1
  fi
}

image_exists() {
  docker image inspect "$1" >/dev/null 2>&1
}

download_file() {
  local url="$1"
  local output="$2"

  mkdir -p "$(dirname "$output")"
  if [[ -s "$output" ]]; then
    log "Using existing download: $output"
    return
  fi

  log "Downloading $url"
  if command -v curl >/dev/null 2>&1; then
    run curl -fL --retry 3 --continue-at - --output "$output" "$url"
  elif command -v wget >/dev/null 2>&1; then
    run wget -c -O "$output" "$url"
  else
    die "curl or wget is required for downloading"
  fi
}

load_image() {
  local package_path="$1"
  log "Loading Docker image package: $package_path"
  run docker load -i "$package_path"
}

first_existing_image() {
  local image
  for image in "$@"; do
    if image_exists "$image"; then
      printf '%s\n' "$image"
      return 0
    fi
  done
  return 1
}

find_pulsar2_candidate() {
  local image
  first_existing_image \
    "$PULSAR2_IMAGE" \
    "pulsar2:latest" \
    "pulsar2:3.3" \
    "sipeed/pulsar2:latest" \
    "axera/pulsar2:6.0" \
    "axera-tech/pulsar2:6.0" && return 0

  while IFS= read -r image; do
    case "$image" in
      *pulsar2*:*)
        printf '%s\n' "$image"
        return 0
        ;;
    esac
  done < <(docker image ls --format '{{.Repository}}:{{.Tag}}')

  return 1
}

tag_image_if_needed() {
  local source_image="$1"
  local target_image="$2"

  if [[ "$source_image" == "$target_image" ]]; then
    return
  fi
  log "Tagging $source_image as $target_image"
  run docker tag "$source_image" "$target_image"
}

verify_pulsar2() {
  [[ "$SKIP_VERIFY" -eq 0 ]] || return
  log "Verifying $PULSAR2_IMAGE"
  run docker run --rm "$PULSAR2_IMAGE" -c "pulsar2 version"
}

setup_pulsar2() {
  log "Preparing Pulsar2 image: $PULSAR2_IMAGE"
  if image_exists "$PULSAR2_IMAGE"; then
    log "$PULSAR2_IMAGE already exists"
    verify_pulsar2
    return
  fi

  if [[ -n "$PULSAR2_SOURCE_IMAGE" ]]; then
    image_exists "$PULSAR2_SOURCE_IMAGE" || die "source image not found: $PULSAR2_SOURCE_IMAGE"
    tag_image_if_needed "$PULSAR2_SOURCE_IMAGE" "$PULSAR2_IMAGE"
    verify_pulsar2
    return
  fi

  if [[ -n "$PULSAR2_TAR" ]]; then
    load_image "$PULSAR2_TAR"
  elif [[ "$DOWNLOAD_PULSAR2" -eq 1 ]]; then
    require_value "$PULSAR2_URL" "--pulsar2-url"
    PULSAR2_TAR="$DOWNLOADS_DIR/$(basename "${PULSAR2_URL%%\?*}")"
    download_file "$PULSAR2_URL" "$PULSAR2_TAR"
    load_image "$PULSAR2_TAR"
  fi

  if image_exists "$PULSAR2_IMAGE"; then
    verify_pulsar2
    return
  fi

  local candidate=""
  if candidate="$(find_pulsar2_candidate)"; then
    tag_image_if_needed "$candidate" "$PULSAR2_IMAGE"
    verify_pulsar2
    return
  fi

  cat >&2 <<EOF
ERROR: $PULSAR2_IMAGE is still missing.

Provide a local Pulsar2 Docker package:
  scripts/setup_toolchains.sh pulsar2 --pulsar2-tar /path/to/ax_pulsar2_6.0.tar.gz

Or explicitly allow downloading:
  scripts/setup_toolchains.sh pulsar2 --download-pulsar2

You can override the URL with --pulsar2-url if the official package location changes.
EOF
  exit 1
}

resolve_tpuc_dev_image() {
  first_existing_image "$TPUC_DEV_IMAGE_V34" "$TPUC_DEV_IMAGE_LATEST"
}

ensure_tpuc_dev_image() {
  local base_image=""
  if base_image="$(resolve_tpuc_dev_image)"; then
    TPUC_BASE_IMAGE="$base_image"
    return
  fi

  if [[ -n "$TPUC_DEV_TAR" ]]; then
    load_image "$TPUC_DEV_TAR"
  elif [[ "$DOWNLOAD_TPUC_DEV" -eq 1 ]]; then
    log "Pulling $TPUC_DEV_IMAGE_LATEST"
    if ! run docker pull "$TPUC_DEV_IMAGE_LATEST"; then
      require_value "$TPUC_DEV_URL" "--tpuc-dev-url"
      TPUC_DEV_TAR="$DOWNLOADS_DIR/$(basename "${TPUC_DEV_URL%%\?*}")"
      download_file "$TPUC_DEV_URL" "$TPUC_DEV_TAR"
      load_image "$TPUC_DEV_TAR"
    fi
  fi

  if base_image="$(resolve_tpuc_dev_image)"; then
    TPUC_BASE_IMAGE="$base_image"
    return
  fi

  cat >&2 <<EOF
ERROR: sophgo/tpuc_dev base image is missing.

Provide a local package:
  scripts/setup_toolchains.sh tpumlir --tpuc-dev-tar /path/to/tpuc_dev_v3.4.tar.gz

Or explicitly allow pulling/downloading:
  scripts/setup_toolchains.sh tpumlir --download-tpuc-dev
EOF
  exit 1
}

verify_tpumlir() {
  [[ "$SKIP_VERIFY" -eq 0 ]] || return
  log "Verifying $TPUMLIR_IMAGE"
  run docker run --rm "$TPUMLIR_IMAGE" model_transform.py --help
  run docker run --rm "$TPUMLIR_IMAGE" model_deploy.py --help
}

setup_tpumlir() {
  log "Preparing TPU-MLIR image: $TPUMLIR_IMAGE"
  if image_exists "$TPUMLIR_IMAGE" && [[ "$FORCE_BUILD" -eq 0 ]]; then
    log "$TPUMLIR_IMAGE already exists"
    verify_tpumlir
    return
  fi

  local base_image=""
  ensure_tpuc_dev_image
  base_image="$TPUC_BASE_IMAGE"
  log "Building $TPUMLIR_IMAGE from $base_image"
  run docker build \
    --build-arg "TPUC_DEV_IMAGE=$base_image" \
    -f "$ROOT_DIR/docker/maixcam-tpumlir.Dockerfile" \
    -t "$TPUMLIR_IMAGE" \
    "$ROOT_DIR"

  verify_tpumlir
}

main() {
  parse_args "$@"
  configure_interactive
  [[ -n "$TARGET" ]] || TARGET="all"
  check_args
  check_docker

  case "$TARGET" in
    all)
      setup_pulsar2
      setup_tpumlir
      ;;
    pulsar2)
      setup_pulsar2
      ;;
    tpumlir)
      setup_tpumlir
      ;;
    *)
      die "unsupported target: $TARGET"
      ;;
  esac

  log "Toolchain image setup finished"
}

main "$@"
