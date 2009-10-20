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

        # Iterator that returns netaddr.IP objects:
        self.ips = []

        self.parse_iprange(iprange)
        # list of netaddr.IP() objects

    # make sure we end up with an ip
    def _find_ip(self, iprange):
        # try to guess if this is an ip or a hostname
        if ip_regex.search(iprange):
            return iprange
        # try to resolve if it looks like a hostname
        # FIXME: thisis blocky and generally icky and failureprone -akl
        ip = socket.gethostbyname(iprange)

        return ip

    def parse_iprange(self, iprange):
        # FIXME: NOTE: all of this stuff is pretty much untested ;-> -akl
        if self.range_str.find(' - ') > -1:
            #looks like a range
            parts = self.range_str.split(' - ')

            #FIXME: all of this error handling is crappy -akl
            try:
                self.start_ip = self._find_ip(parts[0])
                self.end_ip = self._find_ip(parts[1])
            except:
                #FIXME: catchall execpts are bad
                print _("unable to find ip for %s") % parts
                self.start_ip = None
                self.end_ip = None

            if self.start_ip and self.end_ip:
                ipr = netaddr.IPRange(self.start_ip, self.end_ip)
                self.ips = list(ipr)
            return self.ips
        
        # FIXME: not sure what to do about cases like 
        # foo.example.com/24 or "*.example.com". punt? -akl

        if self.range_str.find('/') > -1:
            # looks like a cidr
            cidr = netaddr.CIDR(self.range_str)
            self.ips = list(cidr)
            return self.ips

        if self.range_str.find('*') > -1:
            wildcard = netaddr.Wildcard(self.range_str)
            self.ips = list(wildcard)
            return self.ips

        if ip_regex.search(self.range_str):
            # must be a single ip
            self.start_ip = self._find_ip(self.range_str)
            self.ips = [netaddr.IP(self.start_ip)]
        
        # doesn't look like anything else, try treating it as a hostname
        try:
            self.start_ip = self._find_ip(self.range_str)
            self.ips = [netaddr.IP(self.start_ip)]
        except:
            return None

        return None

    def list_ips(self):
        """ Return a list of individual string IP addresses for this range. """
        return map(str, list(self.ips))
        
    def _gen_list(self):
        pass
    
    def next(self):
        pass

    # implement list style bits?
