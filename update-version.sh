#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 \"version.number\" \"release-message\""
    exit 2
}

if [ "$#" -ne 2 ]; then
    usage
fi

version="$1"
message="$2"

# Validate version format (allow x.y or x.y.z)
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Warning: Version '$version' does not match the standard format x.y or x.y.z."
    echo "Please validate the version number manually."
    read -p "Do you want to continue? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted by user."
        exit 10
    fi
fi

CHANGELOG="debian/changelog"
METAFILE="safeeyes/platform/io.github.slgobinath.SafeEyes.metainfo.xml"
PYPROJECT="pyproject.toml"

if [ ! -f "$CHANGELOG" ]; then
    echo "Error: $CHANGELOG not found." >&2
    exit 1
fi
if [ ! -f "$METAFILE" ]; then
    echo "Error: $METAFILE not found." >&2
    exit 1
fi

# Build maintainer from Git config (do not read debian/control)
# Prefer git user.name and user.email; fall back to sensible defaults
name=$(git config user.name || echo "Unknown")
email=$(git config user.email || echo "unknown@example.com")
maintainer="$name <$email>"


# Dates
rfc_date=$(date -u '+%a, %d %b %Y %H:%M:%S +0000')
iso_date=$(date -u '+%Y-%m-%d')

# Determine distribution string from existing changelog first entry, fallback to 'noble'
dist=$(sed -n '1,120p' "$CHANGELOG" | grep -m1 '^safeeyes (' | sed -n 's/.*) \([^;]*\);.*/\1/p' || true)
if [ -z "$dist" ]; then
    dist="noble"
fi

# Safety checks: do not add duplicate entries
if grep -qF "safeeyes ($version)" "$CHANGELOG" 2>/dev/null; then
    echo "Changelog already contains an entry for version $version; aborting." >&2
    exit 3
fi
if grep -q "version=\"$version\"" "$METAFILE"; then
    echo "Metainfo already contains a release element for version $version; aborting." >&2
    exit 4
fi

# Update pyproject.toml version and Downloads URL if file exists
if [ -f "$PYPROJECT" ]; then
    # Replace version = "..."
    sed -i "s/^version = \".*\"/version = \"$version\"/" "$PYPROJECT"
    # Set Downloads to canonical GitHub archive URL for this version
    # Use a stable URL: https://github.com/slgobinath/safeeyes/archive/v<version>.tar.gz
    sed -i "s#^[[:space:]]*Downloads = \".*\"#Downloads = \"https://github.com/slgobinath/safeeyes/archive/v$version.tar.gz\"#" "$PYPROJECT" || true
    echo "Updated $PYPROJECT"
fi

# Update glade about dialog label if present
GLADE_ABOUT="safeeyes/glade/about_dialog.glade"
if [ -f "$GLADE_ABOUT" ]; then
    # replace 'Safe Eyes x.y.z' inside <property name="label">...<
    sed -i "s/\(<property name=\"label\">Safe Eyes \).*\(<\/property>\)/\1$version\2/" "$GLADE_ABOUT" || true
    echo "Updated $GLADE_ABOUT"
fi



# Prepend changelog entry (Debian format)
tmpfile=$(mktemp)
cat > "$tmpfile" <<EOF
safeeyes ($version) $dist; urgency=medium

  * $message

 -- $maintainer  $rfc_date

EOF

cat "$tmpfile" "$CHANGELOG" > "$CHANGELOG.new" && mv "$CHANGELOG.new" "$CHANGELOG"
rm -f "$tmpfile"
echo "Updated $CHANGELOG"

# Insert release element as the first child under <releases>
# Keep indentation consistent with project file (8 spaces for release lines)
awk -v ver="$version" -v iso="$iso_date" '
/^[[:space:]]*<releases>[[:space:]]*$/ { print; printf "        <release version=\"%s\" date=\"%s\" />\n", ver, iso; next }
{ print }
' "$METAFILE" > "$METAFILE.new" && mv "$METAFILE.new" "$METAFILE"
echo "Updated $METAFILE"

echo "Updated $CHANGELOG and $METAFILE"

exit 0
