from django.utils.translation import gettext_lazy as _
from django.db import models

class ViispKey(models.Model):
    key_content = models.TextField(
        verbose_name=_("key_content"),
        help_text=_('Pgp key content in base64 form'),
    )
    class Meta:
        db_table = 'viispkey'
        managed = True

class ViispTokenKey(models.Model):
    key_content = models.TextField(
        verbose_name=_("key_content"),
        help_text=_('Pgp key content'),
    )
    class Meta:
        db_table = 'viisptokenkey'
        managed = True
