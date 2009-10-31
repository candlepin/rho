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


class _OldNetAddr(object):

    @staticmethod
    def get_address(ip):
        return [netaddr.IP(ip)]

    @staticmethod
    def get_range(start_ip, end_ip):
        return list(netaddr.IPRange(start_ip, end_ip))

    @staticmethod
    def get_network(range_str):
        cidr = netaddr.IP(range_str)
        return list(cidr.iprange())

    @staticmethod
    def get_glob(range_str):
        wildcard = netaddr.Wildcard(range_str)
        return list(wildcard)


class _NewNetAddr(object):

    @staticmethod
    def get_address(ip):
        return [netaddr.IPAddress(ip)]

    @staticmethod
    def get_range(start_ip, end_ip):
        range = netaddr.IPRange(start_ip, end_ip)
        return list(range)

    @staticmethod
    def get_network(range_str):
        network = netaddr.IPNetwork(range_str)
        return [x for x in network]

    @staticmethod
    def get_glob(range_str):
        wildcard = netaddr.IPGlob(range_str)
        return list(wildcard)


class RhoIpRange(object):
    def __init__(self, ipranges):
        if getattr(netaddr, "IP", None) != None:
            # 'old' netaddr
            self.netaddr = _OldNetAddr
        else:
            # version 0.7 or higher
            self.netaddr = _NewNetAddr

        # Iterator that returns netaddr.IP objects:
        self.ips = []

        self.valid = True
        sub_ipranges = self._comma_split(ipranges) 
        for sub_iprange in sub_ipranges:
            ret = self.parse_iprange(sub_iprange)
            if ret is None:
                self.valid = False
                return None
            self.ips.extend(ret)
        # list of netaddr.IP() objects

    # FIXME: only works on ipv4 -akl
    def _is_ip(self, ip):
        is_ip = True
        try:
            socket.inet_aton(ip)
        except socket.error:
            is_ip = False
        return is_ip

    def _comma_split(self, iprange):

        ranges = iprange.split(',')
        # cull any empty strings from leading/trailing/dupe commas
        ranges = [x for x in ranges if x != '']
        ranges = map(string.strip, ranges)
        return ranges

    def parse_iprange(self, range_str):
        ips = []
        if range_str.find(' - ') > -1:
            #looks like a range
            parts = range_str.split(' - ')

            #FIXME: all of this error handling is crappy -akl
            try:
                self.start_ip = parts[0]
                self.end_ip = parts[1]
            except:
                #FIXME: catchall excepts are bad
                print _("unable to find ip for %s") % parts
                self.start_ip = None
                self.end_ip = None

            if self.start_ip and self.end_ip:
                ips = self.netaddr.get_range(self.start_ip, self.end_ip)
            return ips
        
        # FIXME: not sure what to do about cases like 
        # foo.example.com/24 or "*.example.com". punt? -akl

        if range_str.find('/') > -1:
            # looks like a cidr
            # the netaddr.CIDR object is picky about being 
            # "true" CIDR which isn't really something we need to care about
            return self.netaddr.get_network(range_str)

        if range_str.find('*') > -1:
            return self.netaddr.get_glob(range_str)

        if ip_regex.search(range_str) and self._is_ip(range_str):
            # must be a single ip
            self.start_ip = range_str
            return self.netaddr.get_address(self.start_ip)
        
        # doesn't look like anything else, try treating it as a hostname
        try:
            self.start_ip = range_str
            ips = [self.start_ip]
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
