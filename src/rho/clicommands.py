#
# Copyright (c) 2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

""" Rho CLI Commands """

import csv
import os
import string
import sys
import uuid
import re
import subprocess as sp
from collections import defaultdict
from collections import OrderedDict
from copy import copy


import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

from optparse import OptionParser
from getpass import getpass
import simplejson as json
import paramiko


def optional_arg(arg_default):
    def func(option,opt_str,value,parser):
        if parser.rargs and not parser.rargs[0].startswith('-'):
            val=parser.rargs[0]
            parser.rargs.pop(0)
        else:
            val=arg_default
        setattr(parser.values,option.dest,val)
    return func


def multi_arg(option, opt_str, value, parser):
    args = []
    for arg in parser.rargs:
        if arg[0] != "-":
            args.append(arg)
        else:
            del parser.rargs[:len(args)]
            break
    if getattr(parser.values, option.dest):
        args.extend(getattr(parser.values, option.dest))
    setattr(parser.values, option.dest, args)


def _read_key_file(filename):
    keyfile = open(os.path.expanduser(
        os.path.expandvars(filename)), "r")
    sshkey = keyfile.read()
    keyfile.close()
    return sshkey


def _read_hosts_file(filename):
    result = None
    try:
        hosts = file(os.path.expanduser(os.path.expandvars(filename)))
        result = hosts.readlines()
        hosts.close()
    except EnvironmentError, e:
        sys.stderr.write('Error reading from %s: %s\n' % (filename, e))
        hosts.close()
    return result


def _edit_playbook(facts):
    string_to_write = "---\n\n- name: Collect these facts\n" \
                      "  runCmds: name=whatever fact_names=default\n" \
                      "  register: facts_all\n\n" \
                      "- name: record host returned dictionary\n" \
                      "  set_fact:\n    res={{facts_all.meta}}\n"
    if os.path.isfile(facts[0]):
        my_facts = _read_hosts_file(facts[0])
        string_to_write = "---\n\n- name: Collect these facts\n" \
                          "  set_fact:\n    fact_list:\n"
        string_to_write = _stringify_facts(string_to_write, my_facts)
    elif type(facts) == list and len(facts) > 1:
        string_to_write = "---\n\n- name: Collect these facts\n" \
                          "  set_fact:\n    fact_list:\n"
        string_to_write = _stringify_facts(string_to_write, facts)
    elif not facts == ['default']:
        print _("facts can be a file, list or 'default' only")
        sys.exit(1)

    with open('roles/collect/tasks/main.yml', 'w') as f:
        f.write(string_to_write)


def _stringify_facts(string_to_write, facts):
    for f in facts:
        string_to_write += "      - " + f + "\n"

    string_to_write += "\n- name: grab info from list\n" \
                       "  runCmds: name=list_facts fact_names={{fact_list}}\n" \
                       "  register: facts_selected\n\n" \
                       "- name: record host returned dictionary\n" \
                       "  set_fact:\n" \
                       "    res={{facts_selected.meta}}\n"

    return string_to_write


def _create_ping_inventory(profile_ranges, profile_auth_list, forks):
    success_auths = set()
    success_hosts = set()
    success_map = defaultdict(list)
    best_map = defaultdict(list)
    mapped_hosts = []

    string_to_write = "[all]\n"
    for r in profile_ranges:
        reg = "[0-9]*.[0-9]*.[0-9]*.\[[0-9]*:[0-9]*\]"
        r = r.strip(',').strip()
        if not re.match(reg, r):
            string_to_write += r + \
                               ' ansible_ssh_host=' \
                               + r + "\n"
        else:
            string_to_write += r + "\n"

    string_to_write += '\n'

    string_header = copy(string_to_write)

    for a in profile_auth_list:
        f = open('ping-inventory', 'w')
        string_to_write = \
            string_header + \
            "[all:vars]\n" + \
            "ansible_ssh_user=" + \
            a[2]

        if (not a[3] == 'empty') and a[3]:
            auth_pass_or_key = '\nansible_ssh_pass=' + a[3]
        elif a[3] == 'empty':
            auth_pass_or_key = '\n'
        else:
            auth_pass_or_key = "\nansible_ssh_private_key_file=" + a[5] + '\n'

        string_to_write += auth_pass_or_key

        f.write(string_to_write)

        f.close()

        cmd_string = 'ansible all -m' \
                     ' ping  -i ping-inventory -f ' + forks

        my_env = os.environ.copy()
        my_env["ANSIBLE_HOST_KEY_CHECKING"] = "False"

        process = sp.Popen(cmd_string,
                           shell=True,
                           stdout=sp.PIPE,
                           stderr=sp.PIPE,
                           env=my_env)

        out = process.communicate()[0].split('\n')

        for l in range(len(out)):
            if 'pong' in out[l]:
                tup_a = tuple(a)
                success_auths.add(tup_a)
                host_line = out[l - 2]
                host_ip = host_line.split('|')[0].strip()
                success_hosts.add(host_ip)
                if host_ip not in mapped_hosts:
                    best_map[tup_a].append(host_ip)
                    mapped_hosts.append(host_ip)
                success_map[host_ip].append(tup_a)

    success_auths = list(success_auths)
    success_hosts = list(success_hosts)

    return success_auths, success_hosts, best_map, success_map


def _create_hosts_auths_file(success_map):
    with open('host_auth_mapping', 'w') as f:
        string_to_write = ""
        for h, l in success_map.iteritems():
            string_to_write += h + '\n----------------------\n'
            for a in l:
                string_to_write += a[1] + '\n'
            string_to_write += '\n\n'
        f.write(string_to_write)


def _create_main_inventory(success_hosts, best_map, profile):
    string_to_write = "[alpha]\n"

    for h in success_hosts:
        string_to_write += h + ' ansible_ssh_host=' \
                           + h + '\n'

    with open(profile + '_hosts', 'w') as f:
        for a in best_map.keys():
            auth_name = a[1]
            auth_user = a[2]
            auth_pass = a[3]
            auth_key = a[5]

            string_to_write += '\n[' \
                               + auth_name \
                               + ']\n'

            for h in best_map[a]:
                string_to_write += h + ' ansible_ssh_host=' \
                                   + h + " ansible_ssh_user=" \
                                   + auth_user
                if (not auth_pass == 'empty') and auth_pass:
                    auth_pass_or_key = ' ansible_ssh_pass=' + auth_pass + '\n'
                elif auth_pass == 'empty':
                    auth_pass_or_key = '\n'
                else:
                    auth_pass_or_key = " ansible_ssh_private_key_file=" + auth_key + '\n'

                string_to_write += auth_pass_or_key

        f.write(string_to_write)


class CliCommand(object):

    """ Base class for all sub-commands. """
    def __init__(self, name="cli", usage=None, shortdesc=None,
                 description=None):

        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.parser = OptionParser(usage=usage, description=description)
        self.name = name
        self.passphrase = None

    def _validate_port(self, port):
        try:
            int(port)
        except ValueError:
            # aka, we get a string here...
            return False
        if int(port) < 1 or int(port) > 65535:
            return False
        return True

    def _validate_options(self):
        """
        Sub-commands can override to do any argument validation they
        require.
        """
        pass

    def _do_command(self):
        pass

    def _read_config(self, filename, password):
        """
        Read config file and decrypt with the given password.

        Note that password here is the password provided by the user, not the
        actual salted AES key.
        """


    def main(self):

        (self.options, self.args) = self.parser.parse_args()
        # we dont need argv[0] in this list...
        self.args = self.args[1:]


        # Translate path to config file to something absolute and expanded:

        self._validate_options()

        if len(sys.argv) < 2:
            print(self.parser.error(_("Please enter at least 2 args")))


        # do the work, catch most common errors here:

        self._do_command()

        # must take option to reset whenever profiles or auths
        # are updated

        # take the profiles and credentials and package them up
        # in a simple playbook with variables named as given names
        #. Run a simple ansible_playbook to ping and test connections.
        # Record failures and create a new playbook and run on that
        # as long as reset option is not given.


class ScanCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog scan [options] PROFILE")
        shortdesc = _("scan given host profile")
        desc = _("scans the host profile")

        CliCommand.__init__(self, "scan", usage, shortdesc, desc)

        self.parser.add_option("--reset", dest="reset", action="store_true",
                               metavar="RESET", default=False,
                               help=_("Use if profiles/auths have been changed"))

        self.parser.add_option("--profile", dest="profile", metavar="PROFILE",
                               help=_("NAME of the profile - REQUIRED"))

        self.parser.add_option("--facts", dest="facts", metavar="FACTS",
                               action="callback", callback=multi_arg, default=[],
                               help=_("'default' or list"))

        self.parser.add_option("--ansible_forks", dest="ansible_forks", metavar="FORKS",
                               help=_("number of ansible forks"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        # We support two ways to specify profiles, with --profile=blah, or
        # without --profile= and just list profiles in the command. Hack here
        # to treat those raw args as --profiles so the subsequent code has just
        # one path.
        if not self.options.profile:
            print _("No profile specified.")
            sys.exit(1)

        if not self.options.facts:
            print _("No facts specified.")
            sys.exit(1)

        if self.options.ansible_forks:
            try:
                if int(self.options.ansible_forks) <= 0:
                    print _("ansible_forks can only be a positive integer.")
                    sys.exit(1)
            except ValueError:
                print _("ansible_forks can only be a positive integer.")
                sys.exit(1)

    def _do_command(self):

        profile = self.options.profile

        facts = self.options.facts

        forks = self.options.ansible_forks if self.options.ansible_forks else '50'

        profile_exists = False

        profile_auth_list = []
        profile_ranges = []

        with open('profiles', 'r') as f:
            lines = f.readlines()
            for line in lines:
                line_list = line.split(',____,')
                if line_list[0] == profile:
                    profile_exists = True
                    profile_ranges = line_list[1].strip().strip(',').split(',')
                    profile_auths = line_list[2].strip().strip(',').split(',')
                    for a in profile_auths:
                        a = a.strip(',').strip()
                        with open('credentials', 'r') as g:
                            auth_lines = g.readlines()
                            for auth_line in auth_lines:
                                auth_line_list = auth_line.split(',')
                                if auth_line_list[0] == a:
                                    profile_auth_list.append(auth_line_list)
                    break

        if not profile_exists:
            print _("Invalid profile. Create profile first")
            sys.exit(1)

        _edit_playbook(facts)

        if self.options.reset:

            success_auths, success_hosts, best_map, success_map =\
                _create_ping_inventory(profile_ranges, profile_auth_list, forks)

            if not len(success_auths):
                print _('All auths are invalid for this profile')
                sys.exit(1)

            _create_hosts_auths_file(success_map)

            _create_main_inventory(success_hosts, best_map, profile)

        elif not os.path.isfile(profile + '_hosts'):
            print (_("Profile %s has not processed.Please use --reset with profile first.") % profile)
            sys.exit(1)

        cmd_string = 'ansible-playbook pb_one.yml -i ' + profile + '_hosts ' + '-v -f ' + forks

        process = sp.Popen(cmd_string,
                           shell=True,
                           stdout=sp.PIPE,
                           stderr=sp.PIPE)

        out = process.communicate()[0]

        print out

        print _("Scanning has completed. The mapping has been"
                " stored in file 'host_auth_map'. The"
                " facts have been stored in 'report.csv' ")


class ProfileShowCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile show [options]")
        shortdesc = _("show a network profile")
        desc = _("show a network profile")

        CliCommand.__init__(self, "profile show", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("profile name - REQUIRED"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        profile_exists = False
        with open('profiles', 'r') as f:
            lines = f.readlines()
            for line in lines:
                line_list = line.strip().split(',____,')
                if line_list[0] == self.options.name:
                    profile_exists = True
                    profile_str = ', '.join(line_list[0:2] + [line_list[3]])
                    print profile_str

        if not profile_exists:
            print(_("Profile %s does not exist.") % self.options.name)
            sys.exit(1)


class ProfileListCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile list [options]")
        shortdesc = _("list the network profiles")
        desc = _("list the network profiles")

        CliCommand.__init__(self, "profile list", usage, shortdesc, desc)

    def _do_command(self):

        with open('profiles', 'r') as f:
            lines = f.readlines()
            for line in lines:
                print line


class ProfileEditCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile edit [options]")
        shortdesc = _("edits a given profile")
        desc = _("edit a given profile")

        CliCommand.__init__(self, "profile edit", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the profile - REQUIRED"))
        self.parser.add_option("--range", dest="ranges", action="callback",
                               callback=multi_arg,
                               metavar="RANGE", default=[],
                               help=_("IP range to scan. See 'man rho' for supported formats."))
        self.parser.add_option("--hosts", dest="hosts", action="store",
                               metavar="HOST", default='',
                               help=_("File of hostnames to scan."))
        # can only replace auth
        self.parser.add_option("--auth", dest="auth", metavar="AUTH",
                               action="callback", callback=multi_arg, default=[],
                               help=_("auth class to associate with profile"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):

        profile_exists = False
        auth_exists = False

        with open('profiles', 'r') as f:
            lines = f.readlines()

        with open('profiles', 'w') as f:
            for line in lines:
                line_list = line.strip().split(',____,')
                string_id_one = line_list[1]

                if line_list[0] \
                        == self.options.name:
                    string_id_one = ''
                    profile_exists = True

                    range_list = self.options.ranges

                    if self.options.hosts:
                        range_list += _read_hosts_file(self.options.hosts)

                    for r in range_list:
                        string_id_one += ', ' + r

                    string_id_one = string_id_one.strip(',')

                with open('credentials', 'r') as g:
                    auth_lines = g.readlines()

                if self.options.auth:
                    string_id_two = ''
                    string_id_three = ''
                    auth_list = self.options.auth
                    for a in auth_list:
                        for auth_line in auth_lines:
                            line_auth_list = auth_line.strip().split(',')
                            if line_auth_list[1] == a:
                                auth_exists = True
                                string_id_two += line_auth_list[0] + ', '
                                string_id_three += a + ', '

                    line_list[1] = string_id_one.rstrip(',').rstrip(' ')
                    line_list[2] = string_id_two.rstrip(',').rstrip(' ')
                    line_list[3] = string_id_three.rstrip(',').rstrip(' ')
                line_string = ',____,'.join(line_list)
                f.write(line_string + '\n')

                if not auth_exists:
                    print _("Some auths do not exist.")
                    sys.exit(1)

        if not profile_exists:
            print(_("Profile %s does not exist.") % self.options.name)
            sys.exit(1)

        print(_("Profile %s edited" % self.options.name))


class ProfileClearCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog profile clear [--name | --all] [options]")
        shortdesc = _("removes 1 or all profiles from list")
        desc = _("removes profiles")

        CliCommand.__init__(self, "profile clear", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the profile to be removed"))
        self.parser.add_option("--all", dest="all", action="store_true",
                               help=_("remove ALL profiles"))

        self.parser.set_defaults(all=False)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name and not self.options.all:
            self.parser.print_help()
            sys.exit(1)

        if self.options.name and self.options.all:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if self.options.name:
            exists = False
            with open('profiles', 'r') as f:
                lines = f.readlines()

            with open('profiles', 'w') as f:

                for line in lines:
                    line_list = line.strip().split(',')
                    if not line_list[0] == self.options.name:
                        f.write(line)
                    else:
                        exists = True

            if not exists:
                print(_("ERROR: No such profile: %s") % self.options.name)
                sys.exit(1)

        # TODO: remove all profile_hosts files?
        elif self.options.all:
            os.remove('profiles')
            print(_("All network profiles removed"))


class ProfileAddCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prof profile add [options]")
        shortdesc = _("add a network profile")
        desc = _("add a network profile")

        CliCommand.__init__(self, "profile add", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the profile - REQUIRED"))
        self.parser.add_option("--range", dest="ranges", action="callback",
                               callback=multi_arg,
                               metavar="RANGE", default=[],
                               help=_("IP range to scan. See 'man rho' for supported formats."))
        self.parser.add_option("--hosts", dest="hosts", action="store",
                               metavar="HOST", default='',
                               help=_("File of hostnames to scan."))
        self.parser.add_option("--auth", dest="auth", metavar="AUTH",
                               action="callback", callback=multi_arg, default=[],
                               help=_("auth class to associate with profile"))


    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.ranges and not self.options.hosts:
            self.parser.print_help()
            sys.exit(1)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        profile_exists = False

        if os.path.isfile('profiles'):

            with open('profiles', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line_list = line.strip().split(',____,')
                    if line_list[0] == self.options.name:
                        profile_exists = True

            if profile_exists:
                print(_("Profile %s already exists.") % self.options.name)
                sys.exit(1)

        if self.options.hosts:
            self.options.ranges += _read_hosts_file(self.options.hosts)

        regex_list = ['www\[[0-9]*:[0-9]*\].[a-z]*.[a-z]*',
                      '[a-z]*-\[[a-z]*:[a-z]*\].[a-z]*.[a-z]*',
                      '[0-9]*.[0-9]*.[0-9]'
                      '*.\[[0-9]*:[0-9]*\]',
                      '^(([0-9]|[1-9][0-9]|1[0-9]'
                      '{2}|2[0-4][0-9]|25[0-5])\.)'
                      '{3}']

        range_list = self.options.ranges

        for r in range_list:
            match = False
            for reg in regex_list:
                if re.match(reg, r):
                    match = True
            if not match:
                print _("Bad host name/range : %s") % r
                sys.exit(1)

        creds = []
        cred_names = []
        for auth in self.options.auth:
            for a in auth.strip().split(","):
                valid = False
                with open('credentials', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        line_list = line.strip().split(',')
                        if line_list[1] == a:
                            valid = True
                            # add the uuids of credentials
                            creds.append(line_list[0])
                            cred_names.append(line_list[1])

                if not valid:
                    print _("Auth %s does not exist") % a
                    sys.exit(1)

        with open('profiles', 'a') as f:
            profile_list = [self.options.name]\
                           + ['____'] + range_list \
                           + ['____'] + creds \
                           + ['____'] + cred_names
            csv_w = csv.writer(f)
            csv_w.writerow(profile_list)


class AuthEditCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth edit [options]")
        shortdesc = _("edits a given auth")
        desc = _("edit a given auth")

        CliCommand.__init__(self, "auth edit", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the auth - REQUIRED"))

        self.parser.add_option("--sshkeyfile", dest="filename", metavar="FILENAME",
                               help=_("file containing SSH key"))
        self.parser.add_option("--username", dest="username",
                               metavar="USERNAME",
                               help=_("user name for authenticating against target machine - REQUIRED"))
        self.parser.add_option("--password", dest="password",
                               metavar="PASSWORD", action='callback',
                               callback=optional_arg('empty'),
                               help=_("password for authenticating against target machine"))

        self.parser.set_defaults(password=False)

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):

        exists = False

        with open('credentials', 'r') as f:
            lines = f.readlines()

        with open('credentials', 'w') as f:
            for line in lines:
                line_list = line.strip().split(',')
                if line_list[1] \
                        == self.options.name:
                    exists = True
                    if self.options.username:
                        line_list[2] = self.options.username
                    if self.options.password:
                        line_list[3] = self.options.password
                    if self.options.filename:
                        sshkey = _read_key_file(self.options.filename)
                        line_list[4] = sshkey
                line_string = ",".join(line_list)
                f.write(line_string + '\n')

        if not exists:
            print(_("Auth %s does not exist.") % self.options.name)
            sys.exit(1)

        print(_("Auth %s updated") % self.options.name)


class AuthClearCommand(CliCommand):
    # TODO: issue with clear by name

    def __init__(self):
        usage = _("usage: %prog auth clear")
        shortdesc = _("clears out the credentials")
        desc = _("clears out the crendentials")

        CliCommand.__init__(self, "auth clear", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("NAME of the auth credential to be removed"))
        self.parser.add_option("--all", dest="all", action="store_true",
                               help=_("remove ALL auth credentials"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name and not self.options.all:
            self.parser.print_help()
            sys.exit(1)

        if self.options.name and self.options.all:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if self.options.name:
            with open('credentials', 'r') as fr:
                with open('cred-temp', 'w') as tw:
                    for line in fr:
                        tw.write(line)

            with open('cred-temp', 'r') as tr:
                with open('credentials', 'w') as fw:
                    for line in tr:
                        if not line.strip().split(',')[1] \
                                == self.options.name:
                            fw.write(line)

            os.remove('cred-temp')

        elif self.options.all:
            os.remove('credentials')


class AuthShowCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth show [options]")
        shortdesc = _("show auth credential")
        desc = _("show authentication credential")

        CliCommand.__init__(self, "auth show", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("auth credential name - REQUIRED"))
        self.parser.add_option("--showkeys", dest="keys", action="store_true",
                                help=_("show ssh keys in the list"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

    def _do_command(self):
        if not os.path.isfile('credentials'):
            print(_("No auth credentials found"))

        auth_exists = False

        with open('credentials', 'r') as f:
            lines = f.readlines()
            for line in lines:
                line_list = line.strip().split(',')
                if line_list[1] == self.options.name:
                    auth_exists = True
                    if line_list[4] and line_list[3]:
                        if not self.options.showkeys:
                            print ', '.join(line_list[0:3]) + ', ********' + ', ssh-key'
                        else:
                            print ', '.join(line_list[0:3]) + ', ********' + ', '.join(line_list[4])
                    elif not line_list[4]:
                        print ', '.join(line_list[0:3]) + ', ********'
                    else:
                        if not self.options.showkeys:
                            print ', '.join(line_list[0:3]) + ', ssh-key'
                        else:
                            print ', '.join(line_list[0:2]) + ', '.join(line_list[4])

        if not auth_exists:
            print _('Auth %s does not exist' % self.options.name)
            sys.exit(1)


class AuthListCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth list [options]")
        shortdesc = _("list auth credentials")
        desc = _("list authentication credentials")

        CliCommand.__init__(self, "auth list", usage, shortdesc, desc)

    def _do_command(self):
        if not os.path.isfile('credentials'):
            print _('No credentials exist yet.')
            sys.exit(1)

        with open('credentials', 'r') as f:
            lines = f.readlines()
            for line in lines:
                line_list = line.strip().split(',')
                if line_list[3] and line_list[4]:
                    print ', '.join(line_list[0:3]) + ', ********' + ', ssh-key'
                elif not line_list[4]:
                    print ', '.join(line_list[0:3]) + ', ********'
                else:
                    print ', '.join(line_list[0:3]) + ', ssh-key'


class AuthAddCommand(CliCommand):

    def __init__(self):
        usage = _("usage: %prog auth add [options]")
        shortdesc = _("add auth credentials to config")
        desc = _("adds the authorization credentials to the config")

        CliCommand.__init__(self, "auth add", usage, shortdesc, desc)

        self.parser.add_option("--name", dest="name", metavar="NAME",
                               help=_("auth credential name - REQUIRED"))
        self.parser.add_option("--sshkeyfile", dest="filename", metavar="FILENAME",
                               help=_("file containing SSH key"))
        self.parser.add_option("--username", dest="username",
                               metavar="USERNAME",
                               help=_("user name for authenticating against target machine - REQUIRED"))
        self.parser.add_option("--password", dest="password", action='callback',
                               metavar="PASSWORD",
                               callback=optional_arg('empty'),
                               help=_("password for authenticating against target machine"))

    def _validate_options(self):
        CliCommand._validate_options(self)

        if not self.options.name:
            self.parser.print_help()
            sys.exit(1)

        # need to pass in file or username:
        if not self.options.filename \
                and not (self.options.username and
                        self.options.password):
            self.parser.print_help()
            sys.exit(1)

    def _save_cred(self, cred):

        if os.path.isfile('credentials'):
            with open('credentials', 'r') as f:
                dict_reader = csv.DictReader(f, cred.keys())
                for line in dict_reader:
                    if line['name'] == self.options.name:
                        print(_("Auth with name exists"))
                        sys.exit(1)
                f.seek(0)

        with open("credentials", 'a') as f:
            dict_writer = csv.DictWriter(f, cred.keys())
            dict_writer.writerow(cred)
            f.seek(0)

    def _do_command(self):
        cred = {}
        if self.options.filename:
            # using sshkey
            os.system("eval `ssh-agent -s`; ssh-add /home/user/.ssh/user")
            sshkey = _read_key_file(self.options.filename)

            cred = OrderedDict([("id",
                                 uuid.uuid4()),
                                ("name",
                                 self.options.name),
                                ("username",
                                 self.options.username),
                                ("password",
                                 ''),
                                ("ssh-key",
                                 sshkey),
                                ("ssh_key_file",
                                 self.options.filename)])

        elif self.options.username and self.options.password:

            cred = OrderedDict([("id",
                                 uuid.uuid4()),
                                ("name",
                                 self.options.name),
                                ("username",
                                 self.options.username),
                                ("password",
                                 self.options.password),
                                ("ssh-key",
                                 ''),
                                ("ssh_key_file",
                                 self.options.filename)])

        self._save_cred(cred)
