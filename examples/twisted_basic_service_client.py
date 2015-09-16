#!/usr/bin/env python
from minibus import MiniBusTwistedClient
import sys
sys.DONT_WRITE_BYTECODE = True

class ServiceClient(MiniBusTwistedClient):
    def __init__(self):
        MiniBusTwistedClient.__init__(self, name="ServiceClient")
        self.echoback = self.service_func_client("echoback", { }, { })

    @MiniBusTwistedClient.inlineServiceCallbacks
    def run(self):
        response = yield self.echoback("this is a test")
        print "received", response
        response = yield self.echoback("wub wub wub!")
        print "received", response
        self.exit_()


if __name__ == "__main__":
    client = ServiceClient()
    client.exec_()


