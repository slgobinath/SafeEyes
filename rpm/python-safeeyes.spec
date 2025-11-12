Name:           python-safeeyes
Version:        2.2.3
Release:        %autorelease
Summary:        Take periodic breaks to protect your eyes

License:        GPL-3.0-or-later
URL:            https://github.com/slgobinath/SafeEyes
Source:         %{pypi_source safeeyes}

BuildArch:      noarch

BuildRequires:  cairo-gobject-devel
BuildRequires:  gobject-introspection-devel
BuildRequires:  gtk3
BuildRequires:  libnotify
BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  python3-psutil

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


%check
%pyproject_check_import


%files -n python3-safeeyes -f %{pyproject_files}
%_bindir/safeeyes
%python3_sitelib%_datadir/applications/*
%python3_sitelib%_datadir/icons/

%changelog
%autochangelog
