#!/usr/bin/env python
from minibus import MiniBusTwistedClient
import sys
sys.DONT_WRITE_BYTECODE = True

class ServiceClient(MiniBusTwistedClient):
    def __init__(self):
        MiniBusTwistedClient.__init__(self, name="ServiceClient")
        self.echoback = self.service_client("echoback", { }, { }, self.echoback_reply, self.echoback_error)

    def echoback_reply(self, reqstid, data):
        print "Received Reply:", reqstid, data
        self.exit_()

    def echoback_error(self, reqstid, data):
        print "Received Error:", reqstid, data
        self.exit_()

    def run(self):
        idstr = self.echoback("This is a test")
        print "waiting to hear on", idstr

if __name__ == "__main__":
    client = ServiceClient()
    client.exec_()


