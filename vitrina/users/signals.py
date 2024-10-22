from django.db.models.signals import post_save
from django.dispatch import receiver
from vitrina.users.models import User, OldPassword

@receiver(post_save, sender=User)
def update_old_passwords(sender, instance, **kwargs):
    if instance.pk and not OldPassword.objects.filter(user=instance, password=instance.password).exists():
        OldPassword.objects.create(user=instance, password=instance.password, version=1)

        print(f'Old password added: {instance.password}')
        old_passwords = OldPassword.objects.filter(user=instance).order_by('-created')
        # Delete old passwords if there are more than 4
        for old_password in old_passwords[4:]:
            old_password.delete()