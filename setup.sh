#!/bin/bash

BIN_DIR="$HOME/.local/bin"
SERVICE_MENU_DIR="$HOME/.local/share/kio/servicemenus"

usage() {
    echo "Usage: $0 [-i|-u]"
    echo "  -i: Installation"
    echo "  -u: Uninstallation"
    exit 1
}

if [ $# -ne 1 ]; then
    usage
fi

case "$1" in
    -i)
        [ ! -d "$BIN_DIR" ] && mkdir -pv "$BIN_DIR"
        [ ! -d "$SERVICE_MENU_DIR" ] && mkdir -pv "$SERVICE_MENU_DIR"
        cp -v image_resize.py "$BIN_DIR/"
        cp -v image_resize.desktop "$SERVICE_MENU_DIR/"
        echo "Installation successful."
        ;;
    -u)
        rm -fv "$BIN_DIR/image_resize.py" "$SERVICE_MENU_DIR/image_resize.desktop"
        echo "Uninstallation successful."
        ;;
    *)
        usage
        ;;
esac
