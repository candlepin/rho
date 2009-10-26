# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import csv

from rho.log import log

import config
import rho_cmds
import rho_ips
import ssh_jobs


class ScanReport():

    # rho_cmds and the list of rho_cmd_classes in scanner.Scanner to get
    # an idea what fields are available for reports
    csv_format = ["ip", "port", "uname.os", "uname.kernel", "uname.processor", 
                  "uname.hardware_platform", "redhat-release.name",
                  "redhat-release.version", "redhat-release.release",
                  "systemid.system_id", "systemid.username", "instnum.instnum", 
                  "etc-release.etc-release", "cpu.count",
                  #"etc-issue.etc-issue",
                  "auth.type", "auth.username", "auth.name", "error"]
    def __init__(self):
        self.ips = {}
        # ips is a dict of 
        # {'ip:ip', 'uanme.os':unameresults... etc}

    def add(self, ssh_job):
        data = {}
        for rho_cmd in ssh_job.rho_cmds:
            data.update(rho_cmd.data)
        if ssh_job.error:
            self.ips[ssh_job.ip] = {'ip': ssh_job.ip,
                                    'port':ssh_job.port,
                                    'error': ssh_job.error,                          
                                    'auth.type': '',
                                    'auth.name': '',
                                    'auth.username': '',
                                    'auth.password': ''}
        else:
            self.ips[ssh_job.ip] = {'ip': ssh_job.ip,
                                    'port':ssh_job.port,
                                    'auth.type': ssh_job.auth.type,
                                    'auth.name': ssh_job.auth.name,
                                    'auth.username': ssh_job.auth.username,
                                    'auth.password': ssh_job.auth.password}
        self.ips[ssh_job.ip].update(data)

    def report(self, fileobj):
        dict_writer = csv.DictWriter(fileobj, self.csv_format,
                extrasaction='ignore')
        ip_list = self.ips.keys()
        ip_list.sort()
        for ip in ip_list:
            dict_writer.writerow(self.ips[ip])


class Scanner():
    def __init__(self, config=None, cache={}, allow_agent=False):
        self.config = config
        self.profiles = []
        self.cache = cache
        self.allow_agent = allow_agent

        # FIXME: we could probably hook this via a plugin/module loader to
        # make it more dynamic... -akl
        self.default_rho_cmd_classes = [rho_cmds.UnameRhoCmd, 
                                        rho_cmds.RedhatReleaseRhoCmd,
                                        rho_cmds.InstnumRhoCmd,
                                        rho_cmds.SystemIdRhoCmd,
                                        rho_cmds.CpuRhoCmd,
                                        rho_cmds.EtcReleaseRhoCmd,
                                        rho_cmds.EtcIssueRhoCmd]
        self.ssh_jobs = ssh_jobs.SshJobs()
        self.output = []

    def _find_auths(self, authnames):
        """ Return a list of Auth objects for the with the given names. """
        # FIXME: this seems like a reasonable place to plug in a "default" auth
        # if we like, maybe?  -akl
        auth_objs = []
        for authname in authnames:
            auth = self.config.get_auth(authname)
            #FIXME: what do we do if an authname is invalid? 
            # for now, we ignore it
            if auth:
                auth_objs.append(auth)
            else:
                log.warn("No such auth: %s" % authname)

        return auth_objs

    def scan_profiles(self, profilenames):
        missing_profiles = []
        ssh_job_list = []
        for profilename in profilenames:
            profile = self.config.get_profile(profilename)
            if profile is None:
                missing_profiles.append(profilename)
                continue
            ips = []
            for range_str in profile.ranges:
                ipr = rho_ips.RhoIpRange(range_str)
                ips.extend(ipr.list_ips())

            # TODO: remove
            self._find_auths(profile.auth_names)

            for ip in ips:

                # Create a copy of the list of ports and authnames,
                # we're going to modify them if we have a cache hit:
                ports = list(profile.ports)
                authnames = list(profile.auth_names)

                # If a cache hit, move the port/auth to the start of the list:
                if ip in self.cache:
                    log.debug("Cache hit for: %s" % ip)
                    cached_port = self.cache[ip]['port']
                    cached_authname = self.cache[ip]['auth']
                    if cached_port in ports:
                        ports.remove(cached_port)
                        ports.insert(0, cached_port)
                        log.debug("trying port %s first" % cached_port)
                    if cached_authname in authnames:
                        authnames.remove(cached_authname)
                        authnames.insert(0, cached_authname)
                        log.debug("trying auth %s first" % cached_authname)

                sshj = ssh_jobs.SshJob(ip=ip, ports=ports,
                                       auths=self._find_auths(authnames),
                                       rho_cmds=self.get_rho_cmds(),
                                       allow_agent=self.allow_agent)
                ssh_job_list.append(sshj)

            self.ssh_jobs.ssh_jobs = ssh_job_list
            self._run_scan()

        return missing_profiles

    def get_rho_cmds(self, rho_cmd_classes=None):
        if not rho_cmd_classes:
            self.rho_cmd_classes = self.default_rho_cmd_classes
        rho_cmds  = []
        for rho_cmd_class in self.rho_cmd_classes:
            rho_cmds.append(rho_cmd_class())
        return rho_cmds

    def _run_scan(self):
        self.out_queue = self.ssh_jobs.run_jobs(callback=self._callback)
        self.out_queue.join()

    def report(self, fileobj):
        self.ssh_jobs.report.report(fileobj)

    def _callback(self, resultlist=[]):
        for result in resultlist:
#            print "%s:%s %s" % (result.ip, result.returncode, result.output)
            self.output.append((result.ip, result.returncode, result.output))

# import profiles
# profile = profiles.get("webservers")

# assuming profile with be iterable'ish
# for host in profile:
#     # host will be a class 
