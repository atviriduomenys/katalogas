from vitrina.users.models import User


def can_edit_profile(request_user: User, user: User):
    return request_user == user
