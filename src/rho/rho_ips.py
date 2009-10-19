#
# Copyright (c) 2009 Red Hat, Inc.
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import re
import socket

import netaddr

# model of an ip address range
ip_regex = re.compile(r'\d+\.\d+\.\d+\.\d+')


class RhoIpRange(object):
    def __init__(self, iprange):
        self.range_str = iprange
        self.ips = []
        self.parse_iprange(iprange)
        # list of netaddr.IP() objects

    def _check_for_hostname(self, iprange):
        # try to guess if this is an ip or a hostname
        if ip_regex.search(iprange):
            return None
        return iprange

    def parse_iprange(self, iprange):
        # very dumb check to see if this looks like a hostname instead of an ip
        # FIXME: there has to be a better way to do this -akl
        if self._check_for_hostname(iprange):
            self.range_str = socket.gethostbyname(self.range_str)
            # we don't support hostname globbing, so assume a hostname string is
            # a single host
            self.ips = [self.range_str]
            return self.ips


        # FIXME: NOTE: all of this stuff is pretty much untested ;-> -akl
        if self.range_str.find('-') > -1:
            #looks like a range
            parts = self.range_str.split('-')
            self.start_ip = parts[0]
            self.end_ip = parts[1]
            ipr = netaddr.IPRange(self.start_ip, self.end_ip)
            self.ips = list(ipr)
            return self.ips

        if self.range_str.find('/') > -1:
            # looks like a cidr
            cidr = netaddr.CIDR(self.range_str)
            self.ips = list(cidr)
            return self.ips

        if self.range_str.find('*') > -1:
            wildcard = netaddr.Wildcard(self.range_str)
            self.ips = list(wildcard)
            return self.ips

        

        return None
        
        
        
    def _gen_list(self):
        pass
    
    def next(self):
        pass

    # implement list style bits?
