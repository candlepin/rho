# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import config
import ssh_jobs
import rho_cmds

class ScanReport():

    format = """%(ip)s,%(uname.os)s,%(uname.processor)s,%(uname.hardware_platform)s,%(redhat-release.name)s,%(redhat-release.version)s,%(redhat-release.release)s"""
    def __init__(self):
        self.ips = {}
        # ips is a dict of 
        # {'ip:ip', 'uanme.os':unameresults... etc}

    def add(self, ssh_job):
        data = {}
        for rho_cmd in ssh_job.rho_cmds:
            data.update(rho_cmd.data)
#        print data
        self.ips[ssh_job.ip] = {'ip': ssh_job.ip,
                                'auth.type': ssh_job.auth.type,
                                'auth.name': ssh_job.auth.name,
                                'auth.username': ssh_job.auth.username,
                                'auth.password': ssh_job.auth.password}
        self.ips[ssh_job.ip].update(data)
#        print self.ips[ssh_job.ip]
                                

    def report(self):

        # hah, need to print out a real header
        print
        print "#,%s" % self.format
        for ip in self.ips.keys():
            print self.format % self.ips[ip]
            # ip, uname.os, uname.process, uname.hardware_platform, redhat-release.name, redhat-release.version, redhat-release.release

class Scanner():
    def __init__(self):
        self.config = None
        self.profiles = []
#        self.default_rho_cmd_classes= [rho_cmds.UnameRhoCmd]
        self.default_rho_cmd_classes = [rho_cmds.UnameRhoCmd, rho_cmds.RedhatReleaseRhoCmd]
        self.ssh_jobs = ssh_jobs.SshJobs()
        self.output = []

    def scan_profile(self, profilename):
        pass
        # for profie in self.profiles:
        #     for host in profile.ip_range:
        #         self.scan(...)

    def get_rho_cmds(self, rho_cmd_classes=None):
        if not rho_cmd_classes:
            self.rho_cmd_classes = self.default_rho_cmd_classes
        rho_cmds  = []
        for rho_cmd_class in self.rho_cmd_classes:
            rho_cmds.append(rho_cmd_class())
        return rho_cmds

    def scan(self, ip, auth):
        ssh_job = ssh_jobs.SshJob(ip=ip, rho_cmds=self.get_rho_cmds(), auth=auth)
        self.ssh_jobs.ssh_jobs.append(ssh_job)
        self.run_scan()
        self.report()

    def run_scan(self):
        self.out_queue = self.ssh_jobs.run_jobs(callback=self._callback)
        self.out_queue.join()

    def report(self):
        self.ssh_jobs.report.report()

    def _callback(self, resultlist=[]):
        for result in resultlist:
#            print "%s:%s %s" % (result.ip, result.returncode, result.output)
            self.output.append((result.ip, result.returncode, result.output))

# import profiles
# profile = profiles.get("webservers")

# assuming profile with be iterable'ish
# for host in profile:
#     # host will be a class 
