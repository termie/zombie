import github

def get_token(username, password):
  g = github.Github(username, password)
  u = g.get_user()
  auth = u.create_authorization(note='zombie')
  return {'token': auth.token}
