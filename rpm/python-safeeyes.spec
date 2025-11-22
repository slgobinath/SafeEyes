Name:           python-safeeyes
Version:        3.2.0
Release:        %autorelease
Summary:        Take periodic breaks to protect your eyes

License:        GPL-3.0-or-later
URL:            https://github.com/slgobinath/SafeEyes
Source:         %{pypi_source safeeyes}

BuildArch:      noarch

BuildRequires:  cairo-gobject-devel
BuildRequires:  gobject-introspection-devel
BuildRequires:  gtk4
BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  gettext

# for notification plugin
BuildRequires: libnotify
Requires: libnotify

# for audiblealert plugin
Requires: (ffmpeg-free or pipewire-utils)

# for smartpause plugin (optional in pyproject.toml)
BuildRequires: python3-pywayland
Requires: python3-pywayland

# xprintidle does not exist on fedora
#Suggests: xprintidle

# for healthstats plugin (optional in pyproject.toml)
BuildRequires: python3-croniter


# Fill in the actual package description to submit package to Fedora
%global _description %{expand:
Protect your eyes from eye strain using this simple and beautiful, yet extensible break reminder.}

%description %_description

%package -n     python3-safeeyes
Summary:        %{summary}

%description -n python3-safeeyes %_description


%prep
%autosetup -p1 -n safeeyes-%{version}


%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install
# Add top-level Python module names here as arguments, you can use globs
%pyproject_save_files -l safeeyes

# add metainfo
mkdir -p %{buildroot}%{_metainfodir}
install -m 644 safeeyes/platform/io.github.slgobinath.SafeEyes.metainfo.xml %{buildroot}%{_metainfodir}

# add icons
for SIZE_APP in 16 24 32 48 64 128
do
    mkdir -p %{buildroot}%{_datadir}/icons/hicolor/${SIZE_APP}x${SIZE_APP}/apps
    install -p -m 644 safeeyes/platform/icons/hicolor/${SIZE_APP}x${SIZE_APP}/apps/io.github.slgobinath.SafeEyes.png \
      %{buildroot}%{_datadir}/icons/hicolor/${SIZE_APP}x${SIZE_APP}/apps/io.github.slgobinath.SafeEyes.png
done

for SIZE_STATUS in 16 24 32 48
do
    mkdir -p %{buildroot}%{_datadir}/icons/hicolor/${SIZE_STATUS}x${SIZE_STATUS}/status
    install -p -m 644 safeeyes/platform/icons/hicolor/${SIZE_STATUS}x${SIZE_STATUS}/status/* \
      %{buildroot}%{_datadir}/icons/hicolor/${SIZE_STATUS}x${SIZE_STATUS}/status/
done

desktop-file-install \
  --dir=%{buildroot}%{_datadir}/applications \
  safeeyes/platform/io.github.slgobinath.SafeEyes.desktop

%check
%pyproject_check_import


%files -n python3-safeeyes -f %{pyproject_files}
%_bindir/safeeyes
%{_datadir}/icons/*
%{_datadir}/applications/*
%{_metainfodir}/*

%changelog
%autochangelog
