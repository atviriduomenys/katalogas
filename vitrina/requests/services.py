from vitrina.likes.models import UserLike
from vitrina.requests.models import Request
from vitrina.users.models import User


def get_is_liked(user: User, request: Request) -> bool:
    liked = False
    if user.is_authenticated:
        user_like = UserLike.objects.filter(request_id=request.pk, user_id=user.pk)
        if user_like.exists():
            liked = True
    return liked
