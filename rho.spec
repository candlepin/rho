%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name: rho
Version: 0.0.3
Release:        1%{?dist}
Summary: An SSH system profiler

Group: Applications/Internet
License: GPLv2
URL: http://github.com/jmrodri/rho
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


%changelog
* Tue Oct 27 2009 Devan Goodwin <dgoodwin@redhat.com> 0.0.3-1
- Too many features/bugfixes to list. Approaching first release.
* Wed Oct 21 2009 Devan Goodwin <dgoodwin@redhat.com> 0.0.2-1
- Beginning to get usable.
* Thu Oct 15 2009 Devan Goodwin <dgoodwin@redhat.com> 0.0.1-1
- Initial packaging.
