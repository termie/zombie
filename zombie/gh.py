import github

def get_token(username, password):
  g = github.Github(username, password)
  u = g.get_user()
  auth = u.create_authorization(note='zombie')
  return {'token': auth.token}

def get_identity(token):
  g = github.Github(token)
  u = g.get_user()
  return u.login
