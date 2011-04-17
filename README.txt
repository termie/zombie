
OMFGWTF Is Going On Here
========================

Things are still pretty raw, using this file to keep track of ideas and whatnot.

Stuff is starting to stabilize a bit so will begin documentation pretty soon.


Getting Started
===============

you'll need to make a world and a character for that world first.

./tools/generate_world.py foo
./tools/generate_character.py termie foo

From there you'll be able to run world_server and client.

./world_server.py
./client.py

They are both extremely chatty right now.

The client is using TextUi which is a not very advanced interface... basically
it lets you type stuff in and send that to the server, the first word is the
command and the rest of the words are the arguments. Some commands are
intercepted by the UI and result in multiple or alternate commands.



Thoughts
========



A World is like a perspective, it provides you with a startling Location and signs the exits for all locations. Locations can be hosted by third parties but to be part of a world they must be signed by that world.

Most connections consist of a control connection and a pubsub connection.





World
  - id
  - name
  - control_address
  - pubsub_address
  - rsa_pub
  - dsa_pub

    location_default()
    location_get(location_id)


Location
  - id
  - id_token {world_id: ((id, location_sig), world_sig)}
  - dsa_pub
  - name
  - description
  - exits {world_id: [(({direction, to}, location_sig), world_sig)]}


Object
  - id
  - id_token ((id, object_sig), world_sig)
  - dsa_pub
  - name
  - description


Data Access Goals
=================

Data access should be outrageously simple.

- Worlds keep track of locations, and pubkeys of valid users
- Locations keep track of world pubkey, itself, and objects currently in the
  location
- Objects keep track of all their own data
- Data is stored as signed json blobs
- Everybody should be able to replicate the db without anybody being able to impersonate somebody they are not.


==========
Liar, Liar
==========

Lying is expected, the goal is that anybody can always verify the truth.


Avoiding MITM
=============

The key attack point for mitm is to impersonate a character, but you have
in effect a CA with the World acting as the trusted third party.


Establishing a Secure Channel
=============================

Character has a signed identity token: ((id, character_signed) world_signed) which
they return with their rsa_pub, signed.

A look call from Alice to Bob:

  ({method: look,
   target: bob,
   self: alice,
   challenge: {},
   }, alice_sig)

  -> bob returns verifiable response
    {id: bob,
     id_token: ((id, character_signed), world_signed),
     dsa_pub: {},
     rsa_pub: {},
     challenge: {challenge}
    }

If Bob doesn't trust that this is Alice asking:

  ({method: look,
    target: alice,
    self: bob,
    challenge: {},
    }, bob_sig)

And the verifies the look request before responding.

Alice then starts a session with Bob

  ({method: session_start,
    target: bob,
    rsa_pub: {},
    }, alice_sig)

Bob responds

  (alice_rsa_encrypt({session_key: {}), bob_sig)

From then on Alice can use that session key to communicate with Bob.


The Role of Locations
=====================

Locations are mostly mediators and guideposts. Their role is to mediate contact
between objects, provide a common forum and list the objects that are part of the location.

if msg['target'] is an object id in the location the location simply decrypt-encrypts the message and sends it to the target as is.






Scenario:
  One Object looks at another.

  Alice looks at Bob






