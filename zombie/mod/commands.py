from zombie import exception
from zombie import objects
from zombie.mod import locations

def spawn(ctx, parsed):
  user_obj = objects.UserObject.load(ctx)

  if ctx.world.has_object(user_obj):
    raise exception.UserError('already spawned')
  
  if ctx.last_seen:
    ctx.world.spawn(user_obj, ctx.last_seen)
  else:
    ctx.world.spawn(user_obj, ctx.world.default_user_spawn())
