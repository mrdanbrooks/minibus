#!/usr/bin/env python
from minibus import MiniBusTwistedClient
import sys
sys.DONT_WRITE_BYTECODE = True

class ServiceServer(MiniBusTwistedClient):
    def __init__(self):
        MiniBusTwistedClient.__init__(self, name="ServiceServer", cryptokey="secret")
        self.service_func_server("echoback", { }, { }, self.echo)

    def echo(self, data):
        print "got", data
        if data[0].lower() == "x":
            raise Exception("I don't like x")
        return "I said '%s'" % data

if __name__ == "__main__":
    server = ServiceServer()
    server.exec_()
