"""Original own-A103 Scientific allowed_child_roles."""


def allowed_child_roles(child_roles):
    return tuple(role for role in child_roles if role in {'scientific_process', 'literature'})
