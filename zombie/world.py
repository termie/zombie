import eventlet

from zombie import crypt
from zombie import event
from zombie import hooks
from zombie import net
from zombie import shared
from zombie.mod import accounts
from zombie.mod import commands
from zombie.mod import location


class World(event.EventEmitter):
  def __init__(self, name, rsa_priv=None, rsa_pub=None, dsa_priv=None,
               dsa_pub=None, *args, **kw):
    super(World, self).__init__(*args, **kw)
    self.name = name
    self.rsa_priv = rsa_priv
    self.rsa_pub = rsa_pub
    self.dsa_priv = dsa_priv
    self.dsa_pub = dsa_pub
    self.pulses_per_second = 10
  
  @classmethod
  def generate(cls, name):
    rsa_priv = crypt.PrivateCrypterKey.generate(name)
    dsa_priv = crypt.PrivateSignerKey.generate(name)
    return cls.load(name)

  @classmethod
  def load(cls, name):
    rsa_priv = crypt.PrivateCrypterKey.load(name)
    rsa_pub = crypt.PublicEncrypterKey.load(name)
    dsa_priv = crypt.PrivateSignerKey.load(name)
    dsa_pub = crypt.PublicVerifierKey.load(name)
  
    return cls(name=name, rsa_priv=rsa_priv, rsa_pub=rsa_pub,
               dsa_priv=dsa_priv, dsa_pub=dsa_pub)

  def init(self):
    # load everything
    # EVERYTHING
    # pretend these are pluggable hooks
    init_hooks = self._get_init_hooks()
    for f in init_hooks:
      f()

    # self.load_objects()

  def _get_init_hooks(self):
    return [self._init_hooks,
            #self._init_bodies,
            #self._init_room_reset, # reset all rooms
            #self._init_inform,
            #self._init_settings,
            #self._init_externals,
            #self._init_actions,
            #self._init_events,
            self._init_location,
            self._init_accounts,
            self._init_commands,
            #self._init_items,
            #self._init_aliases,
            #self._init_time,
            #self._init_help,
            #self._init_scripts
            ]
  
  def _init_hooks(self):
    pass

  def _init_accounts(self):
    hooks.add('pre_message', accounts.authenticate, 0)
    hooks.add('method_register', accounts.register)
  
  def _init_commands(self):
    hooks.add('method_spawn', commands.spawn)

  def _init_location(self):
    hooks.add('method_spawn', location.last_seen, 0)
    hooks.add('method_default_location', location.default_location)

    #for loc in location.list_all():
    #  def _load_loc(loc):
    #    loc_ref = location.Location.load(loc)
    #    s = net.Server(loc_ref)
    #    l = shared.pool.spawn(s.listen, loc_ref.laddress)
    #    p = shared.pool.spawn(s.publish, loc_ref.paddress)

    #  shared.pool.spawn(_load_loc, loc)

  def handle(self, ctx, parsed, msg, sig):
    ctx['world'] = self

    # mostly for things like authentication
    hooks.run('pre_message', ctx, parsed, msg, sig)

    # things that trigger on every/any message
    hooks.run('message', ctx, parsed)

    # whoever is going to handle this command
    hooks.run('method_' + parsed.get('method'), ctx, parsed)

  def world_loop(self):
    while True:
      eventlet.sleep(1 / self.pulses_per_second)
