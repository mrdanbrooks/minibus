# minibus

## Overview
Conceptually, MiniBus consists of a group of independent or loosely associated processes called *Clients* that can pass messages between each other (even between different machines). 
Such messages are broadcast over named channels called *Topics*.
When one Client *Publishes* (sends) a message over a Topic, any other Clients *Subscribing* (listening) to that Topic will receive the message.
This is called a Publish/Subscribe model, in which information must pushed from the sender to the receiver.

MiniBus also defines remote procedure call (RPC) interface known as *Services* which allows MiniBus Clients known as *Service Clients* to call functions running on other MiniBus Clients known as *Service Servers*.
*Service Servers* advertise their functions by assigning them names which can be used by *Service Clients* to map local functions to the remote ones.
This is called a Request/Reply model, in which information from the server is polled by the client. 
*Services* are implemented using *Topics*.

### Topics


## Bus Protocol
The current version of MiniBus sends all messages over Multicast UDP at address ``228.0.0.5:8005``.
Future versions of the protocol are planned to use a combination of Multicast UDP, TCP, and IPC. 

### Message format
Messages are passed between clients formatted in serialized JSON *packets* defined by a *bus schema*.
The bus schema defines a *packet* to contain a *header* and *data*. 
The *header* is a JSON object consisting of 

## Requires
python-twisted
python-jsonschema
