#!/bin/sh
# Assembles the docker build context and builds the reference image xindi-e2e.
#
# Inputs (see README.md):
#   XINDI_PRINTER_FILES  required: where to take the original helper files of the
#                        printer (/root/uart, /home/mks/gene4.py,
#                        /home/mks/libColPic.so) from. One of:
#                          * a directory containing uart, gene4.py, libColPic.so
#                          * the printer's root file system (eMMC image mount)
#                          * a .tar.gz with the three files (local path or URL)
#   XINDI_CPP_SRC        optional: local checkout of QIDI_Q1_Pro at the pinned
#                        commit; downloaded from GitHub when not set.
#
# Every input is checked against the sha256 manifests in manifests/.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
CTX="$HERE/docker"
CACHE="$CTX/.cache"
MAN="$HERE/manifests"

QIDI_COMMIT=8aaa970c1a7175d0ffc0ca5a29cac92617d5733c
QIDI_URL="https://codeload.github.com/QIDITECH/QIDI_Q1_Pro/tar.gz/$QIDI_COMMIT"
HOSTAP_URL="http://deb.debian.org/debian/pool/main/w/wpa/wpa_2.10.orig.tar.xz"

die() { echo "build_images.sh: $*" >&2; exit 1; }

sha256_check() {  # <dir> <manifest>
    if command -v sha256sum >/dev/null 2>&1; then
        (cd "$1" && sha256sum --quiet -c "$2")
    else
        (cd "$1" && shasum -a 256 --quiet -c "$2")
    fi
}

fetch() {  # <url> <dest>
    curl -fsSL -o "$2.part" "$1" && mv "$2.part" "$2"
}

[ -n "$XINDI_PRINTER_FILES" ] || die "XINDI_PRINTER_FILES is not set (see tests/e2e/README.md)"

mkdir -p "$CACHE"
rm -rf "$CTX/cpp" "$CTX/printer"
mkdir -p "$CTX/cpp" "$CTX/printer"

# --- C++ sources of the original program ------------------------------------
if [ -n "$XINDI_CPP_SRC" ]; then
    SRC="$XINDI_CPP_SRC"
else
    TGZ="$CACHE/QIDI_Q1_Pro-$QIDI_COMMIT.tar.gz"
    if [ ! -f "$TGZ" ]; then
        echo "Downloading QIDI_Q1_Pro@$QIDI_COMMIT ..."
        fetch "$QIDI_URL" "$TGZ"
    fi
    rm -rf "$CACHE/qidi"
    mkdir -p "$CACHE/qidi"
    tar -xzf "$TGZ" -C "$CACHE/qidi" --strip-components=1 \
        "QIDI_Q1_Pro-$QIDI_COMMIT/main.cpp" "QIDI_Q1_Pro-$QIDI_COMMIT/CMakeLists.txt" \
        "QIDI_Q1_Pro-$QIDI_COMMIT/src" "QIDI_Q1_Pro-$QIDI_COMMIT/include"
    SRC="$CACHE/qidi"
fi
cp -r "$SRC/main.cpp" "$SRC/CMakeLists.txt" "$SRC/src" "$SRC/include" "$CTX/cpp/"
sha256_check "$CTX/cpp" "$MAN/cpp-sources.sha256" || die "C++ sources do not match manifests/cpp-sources.sha256"

# --- original helper files of the printer -----------------------------------
P="$XINDI_PRINTER_FILES"
case "$P" in
    http://*|https://*)
        fetch "$P" "$CACHE/printer-files.tar.gz"
        tar -xzf "$CACHE/printer-files.tar.gz" -C "$CTX/printer" ;;
    *.tar.gz|*.tgz)
        tar -xzf "$P" -C "$CTX/printer" ;;
    *)
        if [ -f "$P/root/uart" ]; then
            cp "$P/root/uart" "$P/home/mks/gene4.py" "$P/home/mks/libColPic.so" "$CTX/printer/"
        else
            cp "$P/uart" "$P/gene4.py" "$P/libColPic.so" "$CTX/printer/"
        fi ;;
esac
sha256_check "$CTX/printer" "$MAN/printer-files.sha256" || die "printer files do not match manifests/printer-files.sha256"

# --- hostap (libwpa_client) ---------------------------------------------------
[ -f "$CACHE/wpa_2.10.orig.tar.xz" ] || fetch "$HOSTAP_URL" "$CACHE/wpa_2.10.orig.tar.xz"
sha256_check "$CACHE" "$MAN/hostap.sha256" || die "hostap tarball does not match manifests/hostap.sha256"
cp "$CACHE/wpa_2.10.orig.tar.xz" "$CTX/"

docker build --platform linux/arm64 -t xindi-e2e:latest "$CTX"
