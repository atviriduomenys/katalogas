from typing import List, Dict, Any

from vitrina.likes.models import UserLike
from vitrina.requests.models import Request
from vitrina.users.models import User


def get_structure(request: Request) -> List[Dict[str, Any]]:
    structure_data = request.structure_data.split(";") if request.structure_data else []
    structure = []
    for struct in structure_data:
        data = struct.split(",")
        if data and len(data) == 4:
            structure.append({
                "data_title": data[0],
                "dictionary_title": data[1],
                "data_type": data[2],
                "data_notes": data[3],
            })
    return structure


def get_is_liked(user: User, request: Request) -> bool:
    liked = False
    if user.is_authenticated:
        user_like = UserLike.objects.filter(request_id=request.pk, user_id=user.pk)
        if user_like.exists():
            liked = True
    return liked
