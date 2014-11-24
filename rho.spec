%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name: rho
Version: 0.0.23
Release: 1%{?dist}
Summary: An SSH system profiler

Group: Applications/Internet
License: GPLv2
URL: https://github.com/candlepin/rho
Source0: http://alikins.fedorapeople.org/files/rho/rho-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch: noarch
BuildRequires: python-devel
BuildRequires: python-setuptools
Requires: python-paramiko
Requires: python-netaddr
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
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT
install -D -p -m 644 doc/rho.1 $RPM_BUILD_ROOT%{_mandir}/man1/rho.1

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc README AUTHORS COPYING
%{_bindir}/rho
%{python_sitelib}/*
%{_mandir}/man1/rho.1.gz

%changelog
* Mon Nov 24 2014 jesus m. rodriguez <jesusr@redhat.com> 0.0.23-1
- update doc to reference actual variable used in code (jesusr@redhat.com)
- add an example of using --report (jesusr@redhat.com)

* Thu Aug 07 2014 cnsnyder <csnyder@redhat.com> 0.0.22-1
- update releasers (jesusr@redhat.com)
- add f21 (jesusr@redhat.com)
- add releasers.conf for tito (jesusr@redhat.com)
- Updates docs to describe use of the new report command. (csnyder@redhat.com)
- Updates URL to current git repo url. (csnyder@redhat.com)
- removes the now uncessary pack-scan.sh script (csnyder@redhat.com)
- Adds initconfig command to generate a default config with some preset data. (plus tests) (csnyder@redhat.com)
- Adds report module (and tests) with commands largely matching profile. (csnyder@redhat.com)
- Updates README to include a brief section on the pack-scan.sh script. (csnyder@redhat.com)
- Updates man page with info on option --hosts where appropriate. (csnyder@redhat.com)
- Changes field names to match the changes to the rho_cmds classes. Moves pack-scan.sh to /bin. (csnyder@redhat.com)

* Tue Jul 22 2014 jesus m. rodriguez <jesusr@redhat.com> 0.0.21-1
- Adds a RhoCmd and smoke test for subman facts --list (csnyder@redhat.com)
- Fixes VirtWhatRhoCmd.parse_data() exit code checking. (csnyder@redhat.com)
- Changes test_scan_show_fields() to use assertRaises(). (csnyder@redhat.com)
- Fixes date test. Adds redhat-packages tests for new fields.  (csnyder@redhat.com)
- Uses open() instead of file(). (csnyder@redhat.com)
- Fixes indexes of command results. (csnyder@redhat.com)
- Adds tests for RedhatPackagesRhoCmd. (csnyder@redhat.com)
- Adds tests for fields date.date and cpu.socket_count (csnyder@redhat.com)
- Adds smoke test for VirtWhatRhoCmd. (csnyder@redhat.com)
- Adds new field virt.num_running_guests. (csnyder@redhat.com)
- Pulls virt-what out of VirtRhoCmd and into VirtWhatRhoCmd.  (csnyder@redhat.com)
- Changes PkgInfo separator to required arg. (csnyder@redhat.com)
- Removes unused imports. General code clean up. (csnyder@redhat.com)
- Splits redhat-packages.ratio into two fields. (csnyder@redhat.com)
- Adds install_date and build_date to rpm query. Updates PkgInfo to use these dates. (csnyder@redhat.com)
- Renames MiscRhoCmd to DateRhoCmd and updates fields accordingly.  (csnyder@redhat.com)
- Scanner now defaults to explicit list of default commands in rho_cmds.  (csnyder@redhat.com)
- remove trailing whitespace (jesusr@redhat.com)
- Adds virt.num_guests field to pack-scan report script. (csnyder@redhat.com)
- Adds virt.num_guests field to VirtRhoCmd class. (csnyder@redhat.com)
- Adds default of '' to scan --hosts option (csnyder@redhat.com)
- Adds pack-scan.sh [USERNAME] [/path/to/file_of_hosts] (csnyder@redhat.com)
- Adds --hosts option to the scan command. (csnyder@redhat.com)
- Adds test for profile add --hosts and fixes up other tests (csnyder@redhat.com)
- chmod -x clicommands-tests.py to enable testing with nosetests (csnyder@redhat.com)
- Adds new option --hosts [path/to/file_of_hosts] to add a file of comma seperated hostnames to a profile. (csnyder@redhat.com)
- Adds new cpu report field cpu.socket_count. (csnyder@redhat.com)
- Adds RedHatPackagesRhoCmd that provides fields pertaining to Red Hat packages installed on a system. (csnyder@redhat.com)
- Adds MiscRhoCmd class for all miscellaneous commands. (csnyder@redhat.com)
- Adds virt-what command to help determine virt.virt and virt.type fields (csnyder@redhat.com)
- Scanner loads all cmds defined in rho_cmds and not in NONDEFAULT_CMDS.  (csnyder@redhat.com)
- stylish cleanups for setup.py (alikins@redhat.com)
- Include gettext if we use it. (alikins@redhat.com)
- Remove unused 'string' import. (alikins@redhat.com)
- stylish cleanups (alikins@redhat.com)
- import gettext (alikins@redhat.com)
- autopep8'ify PBKDF2.py (alikins@redhat.com)
- autopep8'ify the code because it needs it. (alikins@redhat.com)
- added rhel 5 dep for python:  python-simplejson (whayutin@thinkdoe.localdomain)

* Wed Nov 18 2009 Adrian Likins <alikins@redhat.com> 0.0.20-1
- RHEL5 is using an even older version of python-netaddr that requires most API
  transmogrifying. Namely, lack of netaddr.IP class. (alikins@redhat.com)

* Fri Nov 13 2009 Adrian Likins <alikins@redhat.com> 0.0.19-1
- Merge Fedora Package review spec changes from Mark McLoughlin
  <markmc@redhat.com> (markmc@redhat.com)
- Add the config file version to the begining of the encrypted config file as
  well (alikins@redhat.com)
- Change the AES ciper mode of CFB and store/retrive a 16bit initialization
  vector for use with CFB. (alikins@redhat.com)
- Use a different salt each time we say the file. (alikins@redhat.com)

* Fri Nov 13 2009 Mark McLoughlin <markmc@redhat.com> - 0.0.16-2
- Include egg info
- Drop the -O1 arg from 'setup.py install'
- Don't chdir for manpage install
- Kill some whitespace

* Wed Nov 11 2009 Adrian Likins <alikins@redhat.com> 0.0.16-1
- Add a RhoCmd class for detecting if we are a virt guest or host
  (alikins@redhat.com)

* Wed Nov 04 2009 Adrian Likins <alikins@redhat.com> 0.0.15-1
- add bits generated to .gitignore (shut up git) (alikins@redhat.com)
- Don't use weird style of classes on 2.4, use Class(object)
  (alikins@redhat.com)
- A few more tweaks to make Queue24 work the same way as the Queue.Queue in
  2.6. (alikins@redhat.com)
- On python2.4 (aka, rhel5) Queue.Queue doesn't have the .join or .task_done
  methods, which we use and like. So check for them and if they aren't there,
  use our own implementation (pretty much c&p from the 2.6 version of
  Queue.Queue). A little ugly, but alas. (alikins@redhat.com)
- use new style classes, python2.4 doesn't like class FOO()
  (alikins@redhat.com)

* Tue Nov 03 2009 Adrian Likins <alikins@redhat.com> 0.0.13-1
- Fix a bug where we weren't actually consuming the Queue if there weren't as
  many or more threads than hosts. (alikins@redhat.com)
- remove --debug option, it doesn't do anything (alikins@redhat.com)

* Sat Oct 31 2009 Devan Goodwin <dgoodwin@rm-rf.ca> 0.0.11-1
- Support Netaddr > 0.7 (jbowes@repl.ca)
- add a DmiRhoCmd. Grab some basic DMI info. (alikins@redhat.com)
- fix wrong help in "rho profile show" (profile, not auth)
  (alikins@redhat.com)

* Thu Oct 29 2009 Adrian Likins <alikins@redhat.com> 0.0.10-1
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
