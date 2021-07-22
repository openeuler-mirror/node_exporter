# Generate devel rpm
%global with_devel 1
# Build project from bundled dependencies
%global with_bundled 1
# Build with debug info rpm
%global with_debug 0
# Run tests in check section
%global with_check 1
# Generate unit-test rpm
%global with_unit_test 0

%if 0%{?with_debug}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif


%global provider        github
%global provider_tld    com
%global project         prometheus
%global repo            node_exporter
# https://github.com/prometheus/node_exporter
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     %{provider_prefix}


Name:           golang-%{provider}-%{project}-%{repo}
Version:        1.0.1
Release:        2
Summary:        Exporter for machine metrics
License:        ASL 2.0
URL:            https://%{provider_prefix}
Source0:        https://%{provider_prefix}/archive/v%{version}.tar.gz
Source1:        sysconfig.node_exporter
Source2:        node_exporter.service
Source3:        node_exporter_textfile_wrapper.sh
Source4:        textfile_collectors_README

Provides:       node_exporter = %{version}-%{release}

BuildRequires:  systemd

# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 aarch64 %{arm}}

%description
%{summary}

%if 0%{?with_devel}
%package devel
Summary:       %{summary}
BuildArch:     noarch

BuildRequires: git
BuildRequires: golang >= 1.14

%description devel
%{summary}

This package contains library source intended for
building other packages which use import path with
%{import_path} prefix.
%endif

%if 0%{?with_unit_test} && 0%{?with_devel}
%package unit-test-devel
Summary:         Unit tests for %{name} package
%if 0%{?with_check}
#Here comes all BuildRequires: PACKAGE the unit tests
#in %%check section need for running
%endif

# test subpackage tests code from devel subpackage
Requires:        %{name}-devel = %{version}-%{release}

%if 0%{?with_check} && ! 0%{?with_bundled}
BuildRequires: golang(github.com/prometheus/client_golang/prometheus/promhttp)
%endif

Requires:      golang(github.com/prometheus/client_golang/prometheus/promhttp)

%description unit-test-devel
%{summary}

This package contains unit tests for project
providing packages with %{import_path} prefix.
%endif

%prep
%setup -q -n %{repo}-%{version}
mkdir -p _build/src/%{provider}.%{provider_tld}/%{project}
ln -s $(pwd) _build/src/%{provider_prefix}

%build
# mkdir -p _build/src/%{provider}.%{provider_tld}/%{project}
# ln -s $(pwd) _build/src/%{provider_prefix}

%if ! 0%{?with_bundled}
export GOPATH=$(pwd)/_build:%{gopath}
%else
# Since we aren't packaging up the vendor directory we need to link
# back to it somehow. Hack it up so that we can add the vendor
# directory from BUILD dir as a gopath to be searched when executing
# tests from the BUILDROOT dir.
ln -s ./ ./vendor/src # ./vendor/src -> ./vendor
export GOPATH=$(pwd)/_build:$(pwd)/vendor:%{gopath}
%endif

# set version information
export LDFLAGS="-X github.com/prometheus/common/version.Version=%{version} -X github.com/prometheus/common/version.BuildUser=copr -X github.com/prometheus/common/version.BuildDate=$(date '+%Y%m%d-%T')"

%if ! 0%{?gobuild:1}
function _gobuild { go build -a -ldflags "-B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \n') $LDFLAGS" -v -x "$@"; }
%global gobuild _gobuild
%endif

# non-modular build
#####
export GOPATH=$(pwd)/_build
#####
export GO111MODULE=off; rm -f go.mod
%gobuild -o _build/node_exporter %{provider_prefix}

%install
install -d -p   %{buildroot}%{_sbindir} \
                %{buildroot}%{_defaultdocdir}/node_exporter \
                %{buildroot}%{_sysconfdir}/sysconfig \
                %{buildroot}%{_sysconfdir}/prometheus/node_exporter/text_collectors

%if 0%{?rhel} != 6
install -d -p   %{buildroot}%{_unitdir}
%endif

install -p -m 0644 %{_sourcedir}/textfile_collectors_README %{buildroot}%{_sysconfdir}/prometheus/node_exporter/text_collectors/README
install -p -m 0644 %{_sourcedir}/sysconfig.node_exporter %{buildroot}%{_sysconfdir}/sysconfig/node_exporter
%if 0%{?rhel} != 6
install -p -m 0644 %{_sourcedir}/node_exporter.service %{buildroot}%{_unitdir}/node_exporter.service
%endif
install -p -m 0755 %{_sourcedir}/node_exporter_textfile_wrapper.sh %{buildroot}%{_sbindir}/node_exporter_textfile_wrapper
install -p -m 0755 ./_build/node_exporter %{buildroot}%{_sbindir}/node_exporter

# source codes for building projects
%if 0%{?with_devel}
install -d -p %{buildroot}/%{gopath}/src/%{import_path}/
echo "%%dir %%{gopath}/src/%%{import_path}/." >> devel.file-list
# find all *.go but no *_test.go files and generate devel.file-list
for file in $(find . \( -iname "*.go" -or -iname "*.s" \) \! -iname "*_test.go" | grep -v "vendor") ; do
    dirprefix=$(dirname $file)
    install -d -p %{buildroot}/%{gopath}/src/%{import_path}/$dirprefix
    cp -pav $file %{buildroot}/%{gopath}/src/%{import_path}/$file
    echo "%%{gopath}/src/%%{import_path}/$file" >> devel.file-list

    while [ "$dirprefix" != "." ]; do
        echo "%%dir %%{gopath}/src/%%{import_path}/$dirprefix" >> devel.file-list
        dirprefix=$(dirname $dirprefix)
    done
done
%endif

# testing files for this project
%if 0%{?with_unit_test} && 0%{?with_devel}
install -d -p %{buildroot}/%{gopath}/src/%{import_path}/
# find all *_test.go files and generate unit-test-devel.file-list
for file in $(find . -iname "*_test.go" | grep -v "vendor") ; do
    dirprefix=$(dirname $file)
    install -d -p %{buildroot}/%{gopath}/src/%{import_path}/$dirprefix
    cp -pav $file %{buildroot}/%{gopath}/src/%{import_path}/$file
    echo "%%{gopath}/src/%%{import_path}/$file" >> unit-test-devel.file-list

    while [ "$dirprefix" != "." ]; do
        echo "%%dir %%{gopath}/src/%%{import_path}/$dirprefix" >> devel.file-list
        dirprefix=$(dirname $dirprefix)
    done
done
%endif

%if 0%{?with_devel}
sort -u -o devel.file-list devel.file-list
%endif

%check
%if 0%{?with_check} && 0%{?with_unit_test} && 0%{?with_devel}
%if ! 0%{?with_bundled}
export GOPATH=%{buildroot}/%{gopath}:%{gopath}
%else
# Since we aren't packaging up the vendor directory we need to link
# back to it somehow. Hack it up so that we can add the vendor
# directory from BUILD dir as a gopath to be searched when executing
# tests from the BUILDROOT dir.
ln -s ./ ./vendor/src # ./vendor/src -> ./vendor

export GOPATH=%{buildroot}/%{gopath}:$(pwd)/vendor:%{gopath}
%endif

%if ! 0%{?gotest:1}
%global gotest go test
%endif

%gotest %{import_path}
%gotest %{import_path}/collector
%endif

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%if 0%{?with_devel}
%files devel -f devel.file-list
%dir %{gopath}/src/%{provider}.%{provider_tld}/%{project}
%endif

%if 0%{?with_unit_test} && 0%{?with_devel}
%files unit-test-devel -f unit-test-devel.file-list
%endif

%files
%if 0%{?rhel} != 6
%{_unitdir}/node_exporter.service
%endif
%config(noreplace) %{_sysconfdir}/sysconfig/node_exporter
%config %{_sysconfdir}/prometheus/node_exporter/text_collectors/README
%license LICENSE
%doc *.md text_collector_examples
%{_sbindir}/*

%pre
getent group node_exporter > /dev/null || groupadd -r node_exporter
getent passwd node_exporter > /dev/null || \
    useradd -rg node_exporter -d /var/lib/node_exporter -s /sbin/nologin \
            -c "Prometheus node exporter" node_exporter
mkdir -p /var/lib/node_exporter/textfile_collector
chgrp node_exporter /var/lib/node_exporter/textfile_collector
chmod 771 /var/lib/node_exporter/textfile_collector

%post
%if 0%{?rhel} != 6
%systemd_post node_exporter.service
%endif

%preun
%if 0%{?rhel} != 6
%systemd_preun node_exporter.service
%endif

%postun
%if 0%{?rhel} != 6
%systemd_postun node_exporter.service
%endif

%changelog
* Sat Feb 21 2021 yangzhao <yangzhao1@kylinos.cn> 1.0.1-2
- Remove unnecessary requirements

* Fri Jun 21 2020 houjian <houjian@kylinos.cn> 1.0.1-1
- Package Init



