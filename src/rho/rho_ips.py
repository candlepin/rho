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
import string

import netaddr

# model of an ip address range
ip_regex = re.compile(r'\d+\.\d+\.\d+\.\d+')


class RhoIpRange(object):
    def __init__(self, ipranges):
        self.range_str = ipranges

        # Iterator that returns netaddr.IP objects:
        self.ips = []

        self.ipranges = self._comma_split(ipranges) 
        for iprange in self.ipranges:
            ret = self.parse_iprange(iprange)
            self.ips.extend(ret)
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

    def _comma_split(self, iprange):
        ranges = iprange.split(',')
        ranges = map(string.strip, ranges)
        return ranges

    def parse_iprange(self, range_str):
        ips = []
        # FIXME: NOTE: all of this stuff is pretty much untested ;-> -akl
        if range_str.find(' - ') > -1:
            #looks like a range
            parts = range_str.split(' - ')

            #FIXME: all of this error handling is crappy -akl
            try:
                self.start_ip = self._find_ip(parts[0])
                self.end_ip = self._find_ip(parts[1])
            except:
                #FIXME: catchall excepts are bad
                print _("unable to find ip for %s") % parts
                self.start_ip = None
                self.end_ip = None

            if self.start_ip and self.end_ip:
                ipr = netaddr.IPRange(self.start_ip, self.end_ip)
                ips = list(ipr)
            return ips
        
        # FIXME: not sure what to do about cases like 
        # foo.example.com/24 or "*.example.com". punt? -akl

        if range_str.find('/') > -1:
            # looks like a cidr
            # the netaddr.CIDR object is picky about being 
            # "true" CIDR which isn't really something we need to care about
            cidr = netaddr.IP(range_str)
            ips = list(cidr.iprange())
            return ips

        if range_str.find('*') > -1:
            wildcard = netaddr.Wildcard(range_str)
            ips = list(wildcard)
            return ips

        if ip_regex.search(range_str):
            # must be a single ip
            self.start_ip = self._find_ip(range_str)
            ips = [netaddr.IP(self.start_ip)]
            return ips
        
        # doesn't look like anything else, try treating it as a hostname
        try:
            self.start_ip = self._find_ip(range_str)
            ips = [netaddr.IP(self.start_ip)]
            return ips
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
