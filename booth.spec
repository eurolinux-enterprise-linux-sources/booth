# RPMs are split as follows:
# * booth:
#   - envelope package serving as a syntactic shortcut to install
#     booth-site (with architecture reliably preserved)
# * booth-core:
#   - package serving as a base for booth-{arbitrator,site},
#     carrying also basic documentation, license, etc.
# * booth-arbitrator:
#   - package to be installed at a machine accessible within HA cluster(s),
#     but not (necessarily) a member of any, hence no dependency
#     on anything from cluster stack is required
# * booth-site:
#   - package to be installed at a cluster member node
#     (requires working cluster environment to be useful)
# * booth-test:
#   - files for testing booth
#
# TODO:
# wireshark-dissector.lua currently of no use (rhbz#1259623), but if/when
# this no longer persists, add -wireshark package (akin to libvirt-wireshark)

%bcond_with html_man
%bcond_with glue

%global specver 6
%global boothver 1.0
# set following to the actual commit or, for final release, concatenate
# "boothver" macro to "v" (will yield a tag per the convention)
%global commit ef769ef9614e8446f597ee4d26d5d339a491ab2f
%global lparen (
%global rparen )
%global shortcommit %(c=%{commit}; case ${c} in
                      v*%{rparen} echo ${c:1};;
                      *%{rparen} echo ${c:0:7};; esac)
%global pre_release %(s=%{shortcommit}; [ ${s: -3:2} != rc ]; echo $?)
%global post_release %([ %{commit} = v%{shortcommit} ]; echo $?)
%global github_owner ClusterLabs

%if 0%{pre_release}
%global boothrel    0.%{specver}.%(s=%{shortcommit}; echo ${s: -3})
%else
%if 0%{post_release}
%global boothrel    %{specver}.%{shortcommit}.git
%else
%global boothrel    %{specver}
%endif
%endif

%{!?_pkgdocdir: %global _pkgdocdir %{_docdir}/%{name}}
# https://fedoraproject.org/wiki/EPEL:Packaging?rd=Packaging:EPEL#The_.25license_tag
%{!?_licensedir:%global license %doc}

%global test_path   %{_datadir}/booth/tests

Name:           booth
Version:        %{boothver}
Release:        %{boothrel}%{dist}
Summary:        Ticket Manager for Multi-site Clusters
Group:          System Environment/Daemons
License:        GPLv2+
Url:            https://github.com/%{github_owner}/%{name}
Source0:        https://github.com/%{github_owner}/%{name}/archive/%{commit}/%{name}-%{shortcommit}.tar.gz
Patch0: 0001-test-README-testing-indent-configuration-literal-par.patch
Patch1: 0002-test-README-testing-provide-pcs-configuration-altern.patch
Patch2: 0003-test-live_test-use-a-defined-literal-uniformly.patch
Patch3: 0004-test-live_test-offer-alternatives-to-crm-pcs-native.patch
Patch4: bz1341720-zealous-local-address-matching.patch
Patch5: bz1366616-local_site_resolved_prevents_segfault.patch

# imposed by the same statement in pacemaker.spec
%if 0%{?rhel} > 0
ExclusiveArch: i686 x86_64 s390x
%endif

# direct build process dependencies
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  coreutils
BuildRequires:  make
## ./autogen.sh
BuildRequires:  /bin/sh
# general build dependencies
BuildRequires:  asciidoc
BuildRequires:  gcc
BuildRequires:  pkgconfig
# linking dependencies
BuildRequires:  libgcrypt-devel
BuildRequires:  libxml2-devel
## just for <pacemaker/crm/services.h> include
BuildRequires:  pacemaker-libs-devel
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  zlib-devel
## logging provider
BuildRequires:  pkgconfig(libqb)
## random2range provider
BuildRequires:  pkgconfig(glib-2.0)
## nametag provider
BuildRequires:  pkgconfig(libsystemd)
# check scriptlet (for hostname and killall respectively)
BuildRequires:  hostname psmisc
BuildRequires:  python2-devel
# spec file specifics
## for _unitdir, systemd_requires and specific scriptlet macros
BuildRequires:  systemd
## for autosetup
BuildRequires:  git

# this is for a composite-requiring-its-components arranged
# as an empty package (empty files section) requiring subpackages
# (_isa so as to preserve the architecture)
Requires:       %{name}-core%{?_isa} = %{version}-%{release}
Requires:       %{name}-site = %{version}-%{release}
%files
# intentionally empty

%description
Booth manages tickets which authorize cluster sites located
in geographically dispersed locations to run resources.
It facilitates support of geographically distributed
clustering in Pacemaker.

# SUBPACKAGES #

%package        core
Summary:        Booth core files (executables, etc.)
Group:          System Environment/Daemons
# for booth-keygen (chown, dd)
Requires:       coreutils
# deal with pre-split arrangement
Conflicts:      %{name} < 1.0-1

%description    core
Core files (executables, etc.) for Booth, ticket manager for
multi-site clusters.

%package        arbitrator
Summary:        Booth support for running as an arbitrator
Group:          System Environment/Daemons
BuildArch:      noarch
Requires:       %{name}-core = %{version}-%{release}
%{?systemd_requires}
# deal with pre-split arrangement
Conflicts:      %{name} < 1.0-1

%description    arbitrator
Support for running Booth, ticket manager for multi-site clusters,
as an arbitrator.

%post arbitrator
%systemd_post booth@.service booth-arbitrator.service

%preun arbitrator
%systemd_preun booth@.service booth-arbitrator.service

%postun arbitrator
%systemd_postun_with_restart booth@.service booth-arbitrator.service

%package        site
Summary:        Booth support for running as a full-fledged site
Group:          System Environment/Daemons
BuildArch:      noarch
Requires:       %{name}-core = %{version}-%{release}
# for crm_{resource,simulate,ticket} utilities
Requires:       pacemaker >= 1.1.8
# for ocf-shellfuncs and other parts of OCF shell-based environment
Requires:       resource-agents
# deal with pre-split arrangement
Conflicts:      %{name} < 1.0-1

%description    site
Support for running Booth, ticket manager for multi-site clusters,
as a full-fledged site.

%package        test
Summary:        Test scripts for Booth
Group:          System Environment/Daemons
BuildArch:      noarch
# runtests.py suite (for hostname and killall respectively)
Requires:       hostname psmisc
Requires:       python(abi) < 3
# any of the following internal dependencies will pull -core package
## for booth@booth.service
Requires:       %{name}-arbitrator = %{version}-%{release}
## for booth-site and service-runnable scripts
## (and /usr/lib/ocf/resource.d/booth)
Requires:       %{name}-site = %{version}-%{release}

%description    test
Automated tests for running Booth, ticket manager for multi-site clusters.

# BUILD #

%prep
%autosetup -n %{name}-%{commit} -S git_am

%build
./autogen.sh
%{configure} \
        --with-initddir=%{_initrddir} \
        --docdir=%{_pkgdocdir} \
        --enable-user-flags \
        %{!?with_html_man:--without-html_man} \
        %{!?with_glue:--without-glue}
%{make_build}

%install
%{make_install}
mkdir -p %{buildroot}/%{_unitdir}
cp -a -t %{buildroot}/%{_unitdir} \
        -- conf/booth@.service conf/booth-arbitrator.service
install -D -m 644 -t %{buildroot}/%{_mandir}/man8 \
        -- docs/boothd.8
ln -s boothd.8 %{buildroot}/%{_mandir}/man8/booth.8
cp -a -t %{buildroot}/%{_pkgdocdir} \
        -- ChangeLog README-testing conf/booth.conf.example
# drop what we don't package anyway (COPYING added via tarball-relative path)
rm -rf %{buildroot}/%{_initrddir}/booth-arbitrator
rm -rf %{buildroot}/%{_pkgdocdir}/README.upgrade-from-v0.1
rm -rf %{buildroot}/%{_pkgdocdir}/COPYING
# tests
mkdir -p %{buildroot}/%{test_path}/conf
cp -a -t %{buildroot}/%{test_path} \
        -- test unit-tests script/unit-test.py
cp -a -t %{buildroot}/%{test_path}/conf \
        -- conf/booth.conf.example
chmod +x %{buildroot}/%{test_path}/test/booth_path
chmod +x %{buildroot}/%{test_path}/test/live_test.sh
mkdir -p %{buildroot}/%{test_path}/src
ln -s -t %{buildroot}/%{test_path}/src \
        -- %{_sbindir}/boothd

%check
# alternatively: test/runtests.py
VERBOSE=1 make check

%files          core
%license COPYING
%doc %{_pkgdocdir}/AUTHORS
%doc %{_pkgdocdir}/ChangeLog
%doc %{_pkgdocdir}/README
%doc %{_pkgdocdir}/booth.conf.example
# core command(s) + man pages
%{_sbindir}/booth*
%{_mandir}/man8/booth*.8*
# configuration
%dir %{_sysconfdir}/booth
%exclude %{_sysconfdir}/booth/booth.conf.example

%files          arbitrator
%{_unitdir}/booth@.service
%{_unitdir}/booth-arbitrator.service

%files          site
# OCF (agent + a helper)
## /usr/lib/ocf/resource.d/pacemaker provided by pacemaker
/usr/lib/ocf/resource.d/pacemaker/booth-site
%dir /usr/lib/ocf/lib/booth
     /usr/lib/ocf/lib/booth/geo_attr.sh
# geostore (command + OCF agent)
%{_sbindir}/geostore
%{_mandir}/man8/geostore.8*
## /usr/lib/ocf/resource.d provided by resource-agents
%dir /usr/lib/ocf/resource.d/booth
     /usr/lib/ocf/resource.d/booth/geostore
# helper (possibly used in the configuration hook)
%dir %{_datadir}/booth
     %{_datadir}/booth/service-runnable

%files          test
%doc %{_pkgdocdir}/README-testing
# /usr/share/booth provided by -site
%{test_path}
# /usr/lib/ocf/resource.d/booth provided by -site
/usr/lib/ocf/resource.d/booth/sharedrsc

%changelog
* Thu Sep 15 2016 Jan Pokorný <jpokorny+rpm-booth@redhat.com> - 1.0-6.ef769ef.git
- fix an issue with identity self-determination based on match
  between the addresses assigned at host and the configured addresses
  when a network-part-of-the-address-only match preceded a possible
  exact address match which would not be even tested if the length
  of the network prefix was the same (no longer for this exact one)
  Resolves: rhbz#1341720
- fix a crash when running booth without determined identity
  (e.g., existing, yet empty configuration) under some circumstances
  Resolves: rhbz#1366616
- make patches be applied using "git am" rather than "git apply"

* Wed Jun 22 2016 Jan Pokorný <jpokorny+rpm-booth@redhat.com> - 1.0-5.77d65dd.git
- update per the the current upstream, most notably the support for
  cluster-glue alternatives has been accepted (separate patches no
  longer needed)
- make the main (envelope) package properly require the subpackages
  of the same version
- add patches allowing for live_test.sh using pcs
- allow building also against s390x architecture
  (per Pacemaker dependency constraint)
  Resolves: rhbz#1302087

* Wed May 25 2016 Jan Pokorný <jpokorny+rpm-booth@redhat.com> - 1.0-3.570876d.git
- update per the changesets recently accepted by the upstream
  (memory/resource leaks fixes, patches previously attached separately
  that make unit test pass, internal cleanups, etc.)
  Resolves: rhbz#1302087

* Mon May 09 2016 Jan Pokorný <jpokorny+rpm-booth@redhat.com> - 1.0-2.eb4256a.git
- update a subset of out-of-tree patches per
  https://github.com/ClusterLabs/booth/pull/22#issuecomment-216936987
- pre-inclusion cleanups in the spec (apply systemd scriptlet operations
  with booth-arbitrator, avoid overloading file implicitly considered %%doc
  as %%license)
  Resolves: rhbz#1302087
  Related (Fedora): rhbz#1314865
  Related (Fedora): rhbz#1333509

* Thu Apr 28 2016 Jan Pokorný <jpokorny+rpm-booth@fedoraproject.org> - 1.0-1.eb4256a.git
- initial build
