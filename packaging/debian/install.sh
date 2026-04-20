#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/yt-cut-merge"
DESKTOP_FILE="$HOME/.local/share/applications/yt-cut-merge.desktop"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Installazione dipendenze..."
sudo apt update
sudo apt install -y python3 python3-tk ffmpeg pipx desktop-file-utils

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "Installazione yt-dlp con pipx..."
  pipx install yt-dlp || true
fi

echo "Reinstallazione pulita in $INSTALL_DIR ..."
sudo rm -rf "$INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR/assets"

echo "Copio sorgenti..."
sudo cp -r "$PROJECT_ROOT/src" "$INSTALL_DIR/"
sudo cp "$PROJECT_ROOT/VERSION" "$INSTALL_DIR/" || true
sudo cp "$PROJECT_ROOT/version.json" "$INSTALL_DIR/" || true

if [ -f "$PROJECT_ROOT/assets/app.png" ]; then
  sudo cp "$PROJECT_ROOT/assets/app.png" "$INSTALL_DIR/assets/"
fi

echo "Creo wrapper di avvio..."
sudo tee "$INSTALL_DIR/run_gui.py" >/dev/null <<'PYEOF'
#!/usr/bin/env python3
import sys

SRC = "/opt/yt-cut-merge/src"
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from yt_cut_merge.gui import main

if __name__ == "__main__":
    main()
PYEOF

sudo chmod +x "$INSTALL_DIR/run_gui.py"

echo "Creo launcher desktop utente..."
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=YT Cut Merge GUI
Comment=Scarica, taglia e unisce clip video
Exec=env PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin python3 $INSTALL_DIR/run_gui.py
Icon=$INSTALL_DIR/assets/app.png
Terminal=false
Type=Application
Categories=AudioVideo;
EOF

chmod +x "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" || true
fi

echo
echo "Installazione completata."
echo
echo "Test consigliati:"
echo "  1) python3 /opt/yt-cut-merge/run_gui.py"
echo "  2) gtk-launch yt-cut-merge"
echo
echo "Se il menu non si aggiorna subito, fai logout/login."
echo
echo "Workdir utente prevista:"
echo "  ~/.local/share/yt-cut-merge/video"
