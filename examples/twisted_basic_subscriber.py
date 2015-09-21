#!/usr/bin/env python
from minibus import MiniBusTwistedClient

class BasicTwistedSubscriber(MiniBusTwistedClient):
    def __init__(self):
        MiniBusTwistedClient.__init__(self, name="BasicTwistedSubscriber")
        self.subscribe("/chatter", {"type": "string"}, self.callback, headers=True)

    def callback(self, headers, data):
        print headers
        print data


if __name__ == "__main__":
    client = BasicTwistedSubscriber()
    client.exec_()

