import json
import uuid

from zombie import gh
from zombie import npc


class Console(npc.ObjectNpc):
  def __init__(self, *args, **kw):
    super(Console, self).__init__(*args, **kw)
    self.sessions = {}

  def cmd_use(self, ctx):
    session = self.sessions.get(ctx.caller_id, {'tick': 0})
    if session['tick'] == 0:
      ctx.reply({'message': 'tick 0'})
    elif session['tick'] == 1:
      ctx.reply({'message': 'tick 1'})
    elif session['tick'] == 2:
      ctx.reply({'message': 'tick 2'})
    session['tick'] += 1
    self.sessions[ctx.caller_id] = session


class GithubConsole(Console):
  """This is a console that tells a user how to associate their github id.

  Flow:
    - give instructions on how to get a token
    - instructions on how to give the token to the console
    - instructions on how to store the card the console gives you
    - instructions on how to use the card the console gives you
    - instructions on how to use the console
  """

  message_0 = """
  Welcome new human.

  There will be a few simple tests to verify that you are mentally fit.
  This is the first one.

  In this test you will verify your identity with github and upon
  completion be provided with an identification card.

  To begin, please use your github tool to acquire a token. You can access it
  as follows:

    >>> token = tool.gh.get_token(<your_username>, <your_password>)

  The tool will establish a secure connection directly with github.

  Once you have your token, show it to the console.

  Hint: if you proxy('the console') it returns an object proxy, so..

    >>> console = proxy('the console')
    >>> console.show(token)

  You can also just do:

    >>> show('the console', token)

  """

  def cmd_use(self, ctx):
    """Tell the user what to do."""
    session = self.sessions.get(ctx.caller_id, {'tick': 0})
    if session['tick'] == 0:
      ctx.reply({'message': self.message_0.strip()})

  def cmd_show(self, ctx, data):
    """Do something cool using the github api."""
    if 'token' in data:
      github_login = gh.get_identity(data['token'])
      item = {'id': uuid.uuid4().hex,
              'description': 'A github identity card for %s' % github_login,
              'github_login': github_login}
      item_s = json.dumps(item)
      signer_id, sig = ctx._sign(item_s)
      ctx.reply({'item': [item_s, signer_id, sig]})
