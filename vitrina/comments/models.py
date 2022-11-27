from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from vitrina.comments.managers import PublicCommentManager


class Comment(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59

    USER = "USER"
    REQUEST = "REQUEST"
    PROJECT = "PROJECT"
    STATUS = "STATUS"
    TYPES = (
        (USER, _("Naudotojo komentaras")),
        (REQUEST, _("Prašymo atverti duomenis komentaras")),
        (PROJECT, _("Duomenų rinkinio įtraukimo į projektą komentaras")),
        (STATUS, _("Statuso keitimo komentaras"))
    )

    INVENTORED = "INVENTORED"
    STRUCTURED = "STRUCTURED"
    OPENED = "OPENED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STATUSES = (
        (INVENTORED, _("Inventorintas")),
        (STRUCTURED, _("Įkelta duomenų struktūra")),
        (OPENED, _("Atvertas")),
        (APPROVED, _("Patvirtintas")),
        (REJECTED, _("Atmestas"))
    )

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    deleted_date = models.DateTimeField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("Comment", blank=True, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey('vitrina_users.User', on_delete=models.CASCADE)
    is_public = models.BooleanField(default=True, verbose_name=_("Viešas komentaras"))
    type = models.CharField(max_length=255, choices=TYPES, default=USER)
    status = models.CharField(max_length=255, blank=True, null=True, choices=STATUSES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='content_type_comments')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    rel_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True,
                                         related_name='rel_content_type_comments')
    rel_object_id = models.PositiveIntegerField(blank=True, null=True)
    rel_content_object = GenericForeignKey('rel_content_type', 'rel_object_id')

    objects = models.Manager()
    public = PublicCommentManager()

    class Meta:
        db_table = 'comment'

    def descendants(self, include_self=False):
        descendants = []
        children = Comment.public.filter(parent_id=self.pk).order_by('created')
        if include_self:
            descendants.append(self)
        for child in children:
            descendants.extend(child.descendants(include_self=True))
        return descendants

    def body_text(self):
        if self.type == self.REQUEST:
            body_text = _(f"Pateiktas naujas prašymas {self.rel_content_object.title}. "
                          f"{self.rel_content_object.description}")
        elif self.type == self.PROJECT:
            body_text = _(f"Šis duomenų rinkinys įtrauktas į {self.rel_content_object.get_title} projektą.")
        elif self.type == self.STATUS:
            body_text = _(f"Statusas pakeistas į {self.get_status_display()}. ")
            if self.body:
                body_text = f"{body_text}\n{self.body}"
        else:
            body_text = self.body
        return body_text


# TODO: To be removed.
class Suggestion(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'suggestion'
