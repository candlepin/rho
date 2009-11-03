#!/usr/bin/python

import unittest

from rho import rho_ips


class TestRhoIps(unittest.TestCase):
    def setUp(self):
        pass
#        self.ipr = rho_ips.RhoIpRange(self.iprange)

    # just for debugging results
    def _cmp_list(self, x_list, y_list):
        in_x_not_in_y = []
        in_y_not_in_x = []
        for x in x_list:
            if x not in y_list:
                in_x_not_in_y.append(x)

        for y in y_list:
            if y not in x_list:
                in_y_not_in_x.append(y)

        print "in_expected not in results: ", in_x_not_in_y
        print "in_ results not in expected: ", in_y_not_in_x

    def _check_ipr(self, iprange, expected):
        self.ipr = rho_ips.RhoIpRange(iprange)
        list_of_ips= list(self.ipr.ips)
        ips = map(str, list_of_ips)
#        list_of_ips = self.ipr.list_ips()
        ips.sort()
        expected.sort()

#        print len(ips), len(expected)
#        print ips[0],ips[-1]
#        print expected[0], expected[-1]
#        self._cmp_list(expected, ips)
#        print  ips, expected
        assert ips == expected

    def testIp(self):
        self._check_ipr("10.0.0.1", ["10.0.0.1"])

    def testLocalhost(self):
        self._check_ipr("localhost", ["localhost"])

    def testCommaSeperatedIps(self):
        self._check_ipr("10.0.0.1,10.0.0.2", ["10.0.0.1", "10.0.0.2"])

    def testCommaSeperatedIpsWithSpaces(self):
        self._check_ipr("10.0.0.1 , 10.0.0.2 ", ["10.0.0.1", "10.0.0.2"])


    def testCommaSeperatedRanges(self):
        self._check_ipr("10.0.0.1 - 10.0.0.2, 10.0.1.1 - 10.0.1.2", 
                        ["10.0.0.1", "10.0.0.2", "10.0.1.1", "10.0.1.2"])

    def testCommaSeperatedTrueCIDR(self):
        self._check_ipr("10.0.0.0/31, 10.0.1.0/31", 
                        ["10.0.0.0", "10.0.0.1", "10.0.1.0", "10.0.1.1"])

    def testIPOver(self):
        self._check_ipr("10.0.0.300", [])

    def testIPTooLong(self):
        self._check_ipr("10.0.2.3.4.5.3.4", [])
#    def testHostname(self):
#        # any suggests for a hostname whose ip won't change?
#        self._check_ipr("bugzilla.redhat.com", ["209.132.176.231"])

#    def testBadHostname(self):
#        self._check_ipr("this-will-never-exist.example.com", [])

    def testWildcard(self):
        expected = []
        for i in range(0,256):
            expected.append("10.0.0.%s" % i)
        self._check_ipr("10.0.0.*", expected)

    def testIpRange(self):
        
        expected = []
        for i in range(1,6):
            expected.append("10.0.0.%s" % i)
        self._check_ipr("10.0.0.1 - 10.0.0.5", expected)

    def testCIDR_24(self):
        expected = []
        for i in range(0,256):
            expected.append("10.0.0.%s" % i)
        self._check_ipr("10.0.0.0/24", expected)

    def testCider(self):
        self._check_ipr("10.0.0.1/31", ["10.0.0.0", "10.0.0.1"])


    def testIpRangeLarge(self):
        expected = []
        for i in range(0,4):
            for j in range(0,256):
                expected.append("10.0.%s.%s" % (i, j))
        self._check_ipr("10.0.0.0 - 10.0.3.255", expected)

    
