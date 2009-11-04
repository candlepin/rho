# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import csv
import sys

import gettext
t = gettext.translation('rho', 'locale', fallback=True)
_ = t.ugettext

# report fields we can use. Add them here so we can show them
# with --report-fields
report_fields = {'ip':_('ip address'),
          'port':_('ssh port'),
          'auth.type':_('type of ssh authentication used'),
          'auth.username':_('username ssh'),
          'auth.name':_('name of authentication class'),
          'error':_('any errors that are found')}




class ScanReport(object):

    # rho_cmds and the list of rho_cmd_classes in scanner.Scanner to get
    # an idea what fields are available for reports
    csv_format = ["ip", "port", "uname.os", "uname.kernel", "uname.processor", 
                  "uname.hardware_platform", "redhat-release.name",
                  "redhat-release.version", "redhat-release.release",
                  "systemid.system_id", "systemid.username", "instnum.instnum", 
                  "etc-release.etc-release", "cpu.count", 
                  "cpu.vendor_id", "cpu.model_name", "dmi.bios-vendor",
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

    # generate a dict to feed to writerow to print a csv header
    def gen_header(self, fields):
        d = {}
        for field in fields:
            d[field] = field
        return d

    def report(self, fileobj, report_format=None):
        csv_format = self.csv_format
        if report_format:
            csv_format = report_format
            
        dict_writer = csv.DictWriter(fileobj, csv_format,
                extrasaction='ignore')
        ip_list = self.ips.keys()
        ip_list.sort()
        if fileobj is not sys.stdout:
            dict_writer.writerow(self.gen_header(self.csv_format))
        for ip in ip_list:
            dict_writer.writerow(self.ips[ip])
