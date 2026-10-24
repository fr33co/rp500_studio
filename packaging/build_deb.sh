#!/bin/sh
# Construye dist/rp500-studio_<versión>_all.deb. Uso: sh packaging/build_deb.sh [versión]
set -e
cd "$(dirname "$0")/.."
VER="${1:-0.2.0}"
PKG=rp500-studio
STAGE="$(mktemp -d)"
ROOT="$STAGE/$PKG"
LIB="$ROOT/usr/lib/$PKG"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$LIB" "$ROOT/usr/bin" "$ROOT/usr/share/applications" "$ROOT/usr/share/doc/$PKG" \
         "$ROOT/usr/share/icons/hicolor/scalable/apps" "$ROOT/DEBIAN"

# aplicación (sin cachés ni datos de usuario)
cp -r rp500_linux/rp500 rp500_linux/assets rp500_linux/run.py "$LIB/"
find "$LIB" -name __pycache__ -prune -exec rm -rf {} +

printf '#!/bin/sh\nexec python3 /usr/lib/%s/run.py "$@"\n' "$PKG" > "$ROOT/usr/bin/$PKG"
cp packaging/rp500-studio.desktop "$ROOT/usr/share/applications/"
cp rp500_linux/assets/app_icon.svg "$ROOT/usr/share/icons/hicolor/scalable/apps/$PKG.svg"
cp README.md "$ROOT/usr/share/doc/$PKG/README.md"
cat > "$ROOT/usr/share/doc/$PKG/copyright" <<C
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: RP500 Studio

Files: *
Copyright: 2026 RP500 Studio contributors
License: GPL-3+

License: GPL-3+
 Este programa es software libre: puede redistribuirlo y/o modificarlo bajo los
 términos de la Licencia Pública General de GNU publicada por la Free Software
 Foundation, ya sea la versión 3 de la Licencia o (a su elección) cualquier
 versión posterior.
 .
 En Debian, el texto completo está en /usr/share/common-licenses/GPL-3.
C

find "$ROOT" -type d -exec chmod 755 {} +
find "$ROOT" -type f -exec chmod 644 {} +
chmod 755 "$ROOT/usr/bin/$PKG"

cat > "$ROOT/DEBIAN/postinst" <<'C'
#!/bin/sh
set -e
python3 -m compileall -q /usr/lib/rp500-studio >/dev/null 2>&1 || true
exit 0
C
cat > "$ROOT/DEBIAN/postrm" <<'C'
#!/bin/sh
set -e
if [ "$1" = remove ] || [ "$1" = purge ]; then
    rm -rf /usr/lib/rp500-studio
fi
exit 0
C
chmod 755 "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/postrm"

SIZE=$(du -sk "$ROOT" | cut -f1)
cat > "$ROOT/DEBIAN/control" <<C
Package: $PKG
Version: $VER
Section: sound
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pyqt5, alsa-utils
Installed-Size: $SIZE
Maintainer: RP500 Studio contributors <noreply@users.noreply.github.com>
Description: Editor no oficial de la DigiTech RP500 para Linux
 Edita por USB-MIDI los presets de la DigiTech RP500: cadena de efectos con todos los
 tipos y parámetros, pedal de expresión, sincronía en vivo, guardado de presets,
 importación y exportación (.rp500p, compatible con gdigi) y respaldo.
 .
 Proyecto no oficial y sin relación con el fabricante. Protocolo basado en gdigi.
C

mkdir -p dist
dpkg-deb --build --root-owner-group "$ROOT" "dist/${PKG}_${VER}_all.deb" >/dev/null
echo "dist/${PKG}_${VER}_all.deb"
