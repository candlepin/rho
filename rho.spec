%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name: rho
Version: 0.0.8
Release:        1%{?dist}
Summary: An SSH system profiler

Group: Applications/Internet
License: GPLv2
URL: http://alikins.fedorapeople.org/files/rho/rho-%{version}-%{release}.tar.gz
Source0: rho-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch: noarch
BuildRequires: python-devel
BuildRequires: python-setuptools
Requires: python-paramiko
# Refactors in 0.7 break backward compat:
Requires: python-netaddr < 0.7
Requires: python-simplejson
Requires: python-crypto

%description
Rho is a tool for scanning your network, logging into systems via SSH, and
retrieving information about them.

%prep
%setup -q 


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
cd doc/
install -D -p -m 644 gzip.1 $RPM_BUILD_ROOT%{_mandir}/man1/rho.1
rm -f $RPM_BUILD_ROOT%{python_sitelib}/*egg-info/requires.txt


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc README AUTHORS COPYING
%{_bindir}/rho
%dir %{python_sitelib}/rho
%{python_sitelib}/rho/*
%{python_sitelib}/rho-*.egg-info
%{_mandir}/man1/rho.1.gz


%changelog
* Thu Oct 29 2009 Adrian Likins <alikins@redhat.com> 0.0.8-1
- add SourceURL
- remove ssh_queue.py
- fix man page install

* Wed Oct 28 2009 Devan Goodwin <dgoodwin@redhat.com> 0.0.6-1
- Fix "rho scan nosuchprofile". (dgoodwin@redhat.com)
- Update README. (dlackey@redhat.com)

* Tue Oct 27 2009 Devan Goodwin <dgoodwin@redhat.com> 0.0.5-1
- Too many features/bugfixes to list. Approaching first release.
* Wed Oct 21 2009 Devan Goodwin <dgoodwin@redhat.com> 0.0.2-1
- Beginning to get usable.
* Thu Oct 15 2009 Devan Goodwin <dgoodwin@redhat.com> 0.0.1-1
- Initial packaging.
