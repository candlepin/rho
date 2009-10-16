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

    def run_scan(self):
        self.out_queue = self.ssh_jobs.run_jobs(callback=self._callback)
        self.out_queue.join()
#        print "="*40
#        print self.output
#        print "="*40

    def _callback(self, resultlist=[]):
        for result in resultlist:
#            print "%s:%s %s" % (result.ip, result.returncode, result.output)
            self.output.append((result.ip, result.returncode, result.output))

# import profiles
# profile = profiles.get("webservers")

# assuming profile with be iterable'ish
# for host in profile:
#     # host will be a class 
