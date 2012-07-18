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
