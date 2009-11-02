# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


from rho.log import log

from rho import rho_cmds
from rho import rho_ips
from rho import ssh_jobs

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext


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
                                        rho_cmds.EtcIssueRhoCmd,
                                        rho_cmds.DmiRhoCmd]
        self.ssh_jobs = ssh_jobs.SshJobs()
        self.output = []

    def get_cmd_fields(self):
        fields = {}
        for cmd in self.default_rho_cmd_classes:
            if cmd.fields:
                    fields.update(cmd.fields)
        return fields

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

            for ip in ips:

                # Create a copy of the list of ports and authnames,
                # we're going to modify them if we have a cache hit:
                ports = list(profile.ports)
                authnames = list(profile.auth_names)

                # If a cache hit, move the port/auth to the start of the list:
                if ip in self.cache:
                    log.debug("Cache hit for: %s" % ip)
                    cached_port = self.cache[ip]['port']
                    log.debug("Cached port: %s %s" % (cached_port,
                        type(cached_port)))
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
        self.ssh_jobs.run_jobs(callback=self._callback)
        
    def report(self, fileobj, report_format=None):
        self.ssh_jobs.output_thread.report.report(fileobj, report_format=report_format)

    def _callback(self, *args):
        print args
#        for result in resultlist:
#            print result
#            print "%s:%s %s" % (result.ip, result.returncode, result.output)
#            self.output.append((result.ip, result.returncode, result.output))

# import profiles
# profile = profiles.get("webservers")

# assuming profile with be iterable'ish
# for host in profile:
#     # host will be a class 
