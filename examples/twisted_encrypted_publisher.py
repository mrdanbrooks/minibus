#!/usr/bin/env python
from minibus import MiniBusTwistedClient
from twisted.internet import task

class EncryptedTwistedPublisher(MiniBusTwistedClient):
    def __init__(self):
        MiniBusTwistedClient.__init__(self, name="EncryptedTwistedPublisher", cryptokey="secret")
        self.pub = self.publisher("/chatter", {"type": "string"})
        self.loop = task.LoopingCall(self.pub, "wub")

    def run(self):
        self.loop.start(1)  # Call once every second

if __name__ == "__main__":
    client = EncryptedTwistedPublisher()
    client.exec_()

