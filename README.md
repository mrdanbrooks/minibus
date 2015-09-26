# minibus

## Overview
Conceptually, a MiniBus network consists of a group of independent and loosely associated processes called *Clients* that can communicate with each other by passing messages (even between different machines). 
Such messages are broadcast over named channels called *Topics*.
When one Client *Publishes* (sends) a message over a Topic, any other Clients *Subscribing* (listening) to that Topic will receive the message.
This is called a Publish/Subscribe model, in which information must pushed from the sender to the receiver.

MiniBus also defines a remote procedure call (RPC) interface known as *Services* which allows MiniBus Clients known as *Service Clients* to call functions running on other MiniBus Clients known as *Service Servers*.
*Service Servers* advertise their functions by assigning them names which can be used by *Service Clients* to map local functions to the remote ones.
This is called a Request/Reply model, in which information from the server is polled by the client. 
*Services* are implemented using *Topics*.

### Topics
When a *client* publishes a message on MiniBus, it must specify a name for the topic it will be published on.
When a different *client* wishes to receive that same message, it must specify that it wants to listen to the topic of the same name.

#### Message Schema (Types)
Any data structure which can be serialized into JSON can be sent over Minibus. 
MiniBus topics do not have any particular message type associated with them.
Instead, each client that connects to a topic as a publisher or subscriber can specifies a message schema (or data format) they expect messages to be in.
Message schema are in the form of JSON Schema, and can be as generic or specific as you wish.
For example, the schema ``{ }`` will accept all messages while the schema ``{"type": "string"}`` accepts only strings.
For more information on writing schema, check out [json-schema.org](www.json-schema.org).

#### Topic Names and Namespaces
Topic names are formatted using namespaces.
A namespace is similar to a unix file system directory.
All topics must begin with a forward slash ``/`` followed by some name. 
These names would make up the *root namespace*.
Adding additional forward slashes ``/`` adds a sub namespace.

Namespaces are purely for organizational purposes and do not have any other special function inside MiniBus.
However, *subscribers* can use regular expressions to listen to multiple topics at the same time, and namespaces make it easy to leverage this feature.

Some topic names can have special meanings. 
For example, names that start and end with a double underscore are not displayed by the ``mbtt`` tool (e.g. ``__hidden_topic__``).
This convention does not hide topics from other client, rather it is mostly used to mask internal components of the minibus system. 


## Bus Protocol
The current version of MiniBus sends all messages over Multicast UDP at address ``228.0.0.5:8005``.
Future versions of the protocol are planned to use a combination of Multicast UDP, TCP, and IPC. 

### Message format
Messages are passed between clients formatted in serialized JSON *packets* defined by a *bus schema*.
The bus schema defines a *packet* to contain a *header* object and a *data* field. 
The *header* is a JSON object consisting of the topic name as a string.
The *data* field contains a string with the message as a serialized JSON object inside it. 

## Requires
python-twisted
python-jsonschema
