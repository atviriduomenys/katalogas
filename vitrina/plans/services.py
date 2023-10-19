

def has_plan_close_permission(user, plan):
    if user.is_authenticated:
        if user.is_staff or user.is_superuser:
            return True
        if user.organization:
            if plan.provider:
                return plan.provider == user.organization
            elif plan.receiver:
                return plan.receiver == user.organization
    return False
