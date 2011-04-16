import logging

from zombie import crypt
from zombie import event
from zombie import kvs
from zombie import util


class Node(event.EventEmitter):
  prefix = 'node'

  def __init__(self, id, name=None, rsa_priv=None, rsa_pub=None, dsa_priv=None,
               dsa_pub=None, signed_rsa_pub=None, signed_dsa_pub=None, **kw):
    self.id = id
    self.name = name
    self.rsa_priv = rsa_priv
    self.rsa_pub = rsa_pub
    self.dsa_priv = dsa_priv
    self.dsa_pub = dsa_pub
    self.signed_rsa_pub = signed_rsa_pub
    self.signed_dsa_pub = signed_dsa_pub
    self._protected = {}
    self._protected['look'] = self.do_look

  @classmethod
  def Generate(cls, id, name):
    rsa_priv = crypt.PrivateCrypterKey.generate(id)
    dsa_priv = crypt.PrivateSignerKey.generate(id)
    rsa_pub = crypt.PublicEncrypterKey.load(id)
    dsa_pub = crypt.PublicVerifierKey.load(id)

    node = cls(id=id,
               name=name,
               rsa_priv=rsa_priv,
               rsa_pub=rsa_pub,
               dsa_priv=dsa_priv,
               dsa_pub=dsa_pub)

    return node

  @classmethod
  def Load(cls, id, load_keys=True):
    r = kvs.Storage(cls.prefix)
    d = util.loads(r.get(id))
    d['rsa_priv'] = crypt.PrivateCrypterKey.load(id)
    d['rsa_pub'] = crypt.PublicEncrypterKey.load(id)
    d['dsa_priv'] = crypt.PrivateSignerKey.load(id)
    d['dsa_pub'] = crypt.PublicVerifierKey.load(id)
    return cls.FromDict(d)

  @classmethod
  def FromDict(cls, d):
    logging.debug('d: %s', str(d))
    return cls(**d)

  def sign(self, s):
    return self.dsa_priv.sign(s)

  def sign_node(self, other):
    rsa_pub_s = util.dumps([other.id, str(other.rsa_pub)])
    dsa_pub_s = util.dumps([other.id, str(other.dsa_pub)])

    other.signed_rsa_pub = (rsa_pub_s, self.id, self.dsa_priv.sign(rsa_pub_s))
    other.signed_dsa_pub = (dsa_pub_s, self.id, self.dsa_priv.sign(dsa_pub_s))

  def trust_key(self, trusted_id, trusted_key):
    new_key = crypt.PublicVerifierKey.from_key(
        self.id + '|ca|' + trusted_id, str(trusted_key))
    new_key.save()

  def verify_trusted_sig(self, s, trusted_id, trusted_sig):
    verifier_key = crypt.PublicVerifierKey.load(self.id + '|ca|' + trusted_id)
    if verifier_key.verify(s, trusted_sig):
      return True
    return False

  def save(self):
    r = kvs.Storage(self.prefix)
    d = self.to_dict()
    r.set(self.id, util.dumps(d))
    for keyname in ('rsa_priv', 'rsa_pub', 'dsa_priv', 'dsa_pub'):
      key = getattr(self, keyname)
      if key:
        key.save()
    return self

  def to_dict(self):
    out = {'id': self.id,
           'name': self.name}
    if self.signed_rsa_pub:
      out['signed_rsa_pub'] = self.signed_rsa_pub
    if self.signed_dsa_pub:
      out['signed_dsa_pub'] = self.signed_dsa_pub
    return out

  def handle(self, ctx, request, msg, sig):
    # This is the lowest level handler, it assumes the request has already
    # been authenticated to whatever level was necessary
    if 'method' in request and request['method'] in self._protected:
      return self._protected[request['method']](ctx, request, msg, sig)

  def do_look(self, ctx, request, msg, sig):
    ctx.reply(request, {'node': self.to_dict()})


class SecureNode(Node):
  """A SecureNode requires a session before it will allow most methods."""
  def __init__(self, *args, **kw):
    super(SecureNode, self).__init__(*args, **kw)
    self._public = {}
    self._public['look'] = self.do_public_look
    self._public['session_start'] = self.do_session_start

  def handle(self, ctx, request, msg, sig):
    try:
      session_key = crypt.SessionKey.load(self.id + ctx['client_id'])
      decrypted = session_key.decrypt(msg)
      ctx['session_key'] = session_key
    except Exception:
      session_key = None

    if not session_key:
      if 'method' in request and request['method'] in self._public:
        return self._public[request['method']](ctx, request, msg, sig)
      return

    try:
      new_request = util.loads(decrypted)
    except Exception:
      logging.exception('bad msg')
      return

    return super(SecureNode, self).handle(ctx, new_request, msg, sig)

  def do_public_look(self, ctx, request, msg, sig):
    """Public version of look.

    Request:
      {method: 'look',
       uuid: <uuid>
       }

    Response:
      {uuid: <uuid>,
       node: {id: <id>,
              dsa_pub: #(<dsa_pub>),
              }
       }
    """
    ctx.reply(request, {'node': {'id': self.id, 'dsa_pub': str(self.dsa_pub)}})

  def do_session_start(self, ctx, request, msg, sig):
    """Start a session.

    Request:
      {method: 'session_start',
       signed_rsa_pub: (#(<id>, #(<rsa_pub>)), trusted_id, trusted_sig)
       uuid: <uuid>
       }

    Response:
      {uuid: <uuid>,
       session_key: rsa_pub.encrypt(#(<session_key>))
       }
    """

    session_key = crypt.SessionKey.generate(self.id + ctx['client_id'])
    signed_rsa_pub_s, trusted_id, trusted_sig = request.get('signed_rsa_pub')
    id, rsa_pub_s = util.loads(signed_rsa_pub_s)

    encrypter = crypt.PublicEncrypterKey.from_key(ctx['client_id'],
                                                  rsa_pub_s)

    e_session_key = encrypter.encrypt(str(session_key))
    out = {'session_key': e_session_key}
    ctx.reply(request, out)


class AuthenticatedNode(SecureNode):
  """AuthenticatedNode requires proof of identity before starting a session."""

  def do_session_start(self, ctx, request, msg, sig):
    """Start a session if we know who you are.

    Request:
      {method: 'session_start',
       signed_rsa_pub: (#(<id>, #(<rsa_pub>)), trusted_id, trusted_sig)
       uuid: <uuid>
       }

    Response:
      Same as SecureNode.do_session_start

    """
    signed_rsa_pub_s, trusted_id, trusted_sig = request.get('signed_rsa_pub')
    if not verify_trusted_sig(signed_rsa_pub_s, trusted_id, trusted_sig):
      return

    id, rsa_pub_s = util.loads(signed_rsa_pub_s)
    rv = super(AuthenticatedNode, self).do_session_start(
        ctx, request, msg, sig)
    return rv
