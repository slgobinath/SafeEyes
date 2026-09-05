# Maintainer: gobinath <slgobinathATgmailDOTcom>
# Contributor: yigits <yigitATyigitseverDOTcom>
# Contributor: otuva <onralpakinATgmailDOTcom>
# Contributor: PopeRigby <poperigbyATmailboxDOTorg>
# Maintainer: ilario <iochesonomeATgmailDOTcom>
# Maintainer: archisman <apandada1ATgmailDOTcom>

pkgname=safeeyes
pkgver=3.5.1
pkgrel=1
pkgdesc="A Free and Open Source tool for Linux users to reduce and prevent repetitive strain injury (RSI)."
arch=("any")
url="https://github.com/slgobinath/safeeyes"
license=("GPL3")
depends=("libnotify"
         "gtk4"
         "python-babel"
         "python-gobject"
         "python-packaging"
         "python-psutil"
         "python-xlib")
makedepends=("git" "python-packaging" "python-pip")
optdepends=("python-pywayland: for Smart Pause plugin in Wayland" "xprintidle: for Smart Pause plugin in X11" "ffmpeg: For playing the audible bell" "python-croniter: for Health Stats plugin" "snixembed: For tray icon support in LXDE/MATE/WMs")
source=("git+$url.git#tag=v$pkgver")
sha1sums=('SKIP')

package() {
    cd "$srcdir/safeeyes"
    # Use pip so pyproject.toml (PEP 517) is respected; ensure files declared
    # as data_files in pyproject are installed under /usr when using --prefix=/usr
    python -m pip install --root="$pkgdir" --prefix=/usr --no-deps --ignore-installed .

        # Copy desktop file and icons from site-packages into /usr/share
        sitepkg_dir=$(find "$pkgdir/usr/lib" -maxdepth 3 -type d -name "site-packages" -print -quit)
        if [ -n "$sitepkg_dir" ]; then
            mappings=(
                "safeeyes/platform/io.github.slgobinath.SafeEyes.desktop usr/share/applications"
                "safeeyes/platform/icons/hicolor/128x128/apps/io.github.slgobinath.SafeEyes.png usr/share/icons/hicolor/128x128/apps"
                "safeeyes/platform/icons/hicolor/16x16/apps/io.github.slgobinath.SafeEyes.png usr/share/icons/hicolor/16x16/apps"
                "safeeyes/platform/icons/hicolor/16x16/status/io.github.slgobinath.SafeEyes-disabled.png usr/share/icons/hicolor/16x16/status"
                "safeeyes/platform/icons/hicolor/16x16/status/io.github.slgobinath.SafeEyes-enabled.png usr/share/icons/hicolor/16x16/status"
                "safeeyes/platform/icons/hicolor/16x16/status/io.github.slgobinath.SafeEyes-timer.png usr/share/icons/hicolor/16x16/status"
                "safeeyes/platform/icons/hicolor/24x24/apps/io.github.slgobinath.SafeEyes.png usr/share/icons/hicolor/24x24/apps"
                "safeeyes/platform/icons/hicolor/24x24/status/io.github.slgobinath.SafeEyes-disabled.png usr/share/icons/hicolor/24x24/status"
                "safeeyes/platform/icons/hicolor/24x24/status/io.github.slgobinath.SafeEyes-enabled.png usr/share/icons/hicolor/24x24/status"
                "safeeyes/platform/icons/hicolor/24x24/status/io.github.slgobinath.SafeEyes-timer.png usr/share/icons/hicolor/24x24/status"
                "safeeyes/platform/icons/hicolor/32x32/apps/io.github.slgobinath.SafeEyes.png usr/share/icons/hicolor/32x32/apps"
                "safeeyes/platform/icons/hicolor/32x32/status/io.github.slgobinath.SafeEyes-disabled.png usr/share/icons/hicolor/32x32/status"
                "safeeyes/platform/icons/hicolor/32x32/status/io.github.slgobinath.SafeEyes-enabled.png usr/share/icons/hicolor/32x32/status"
                "safeeyes/platform/icons/hicolor/48x48/apps/io.github.slgobinath.SafeEyes.png usr/share/icons/hicolor/48x48/apps"
                "safeeyes/platform/icons/hicolor/48x48/status/io.github.slgobinath.SafeEyes-disabled.png usr/share/icons/hicolor/48x48/status"
                "safeeyes/platform/icons/hicolor/48x48/status/io.github.slgobinath.SafeEyes-enabled.png usr/share/icons/hicolor/48x48/status"
            )

            for m in "${mappings[@]}"; do
                src_rel=${m%% *}
                dest_dir=${m#* }
                src_path="$sitepkg_dir/$src_rel"
                if [ -f "$src_path" ]; then
                    mkdir -p "$pkgdir/$dest_dir"
                    install -Dm644 "$src_path" "$pkgdir/$dest_dir/$(basename "$src_rel")"
                fi
            done
        fi
}
