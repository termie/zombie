from zombie import exception
from zombie import objects
from zombie.mod import accounts
from zombie.mod import location


@accounts.auth_required
def spawn(ctx, parsed):
  user_obj = objects.UserObject.load(ctx)

  world = ctx.get('world')
  if world.has_object(user_obj):
    raise exception.UserError('already spawned')

  if ctx.last_seen:
    world.spawn(user_obj, ctx['last_seen'])
  else:
    world.spawn(user_obj, world.default_user_spawn())
