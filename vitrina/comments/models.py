from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from vitrina.comments.managers import PublicCommentManager
from vitrina.requests.models import Request


class Comment(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59

    USER = "USER"
    REQUEST = "REQUEST"
    PROJECT = "PROJECT"
    STATUS = "STATUS"
    PLAN = "PLAN"
    STRUCTURE = "STRUCTURE"
    STRUCTURE_ERROR = "STRUCTURE_ERROR"
    TYPES = (
        (USER, _("Naudotojo komentaras")),
        (REQUEST, _("Prašymo atverti duomenis komentaras")),
        (PROJECT, _("Duomenų rinkinio įtraukimo į projektą komentaras")),
        (STATUS, _("Statuso keitimo komentaras")),
        (PLAN, _("Įtraukimo į planą komentaras")),
        (STRUCTURE, _("Struktūros importavimo komentaras")),
        (STRUCTURE_ERROR, _("Struktūros importavimo klaida")),
    )

    INVENTORED = "INVENTORED"
    PLANNED = "PLANNED"
    OPENED = "OPENED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STATUSES = (
        (INVENTORED, _("Inventorintas")),
        (PLANNED, _("Planuojamas atverti")),
        (OPENED, _("Atvertas")),
        (APPROVED, _("Įvertintas")),
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
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='content_type_comments',
        null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    rel_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True,
                                         related_name='rel_content_type_comments')
    rel_object_id = models.PositiveIntegerField(blank=True, null=True)
    rel_content_object = GenericForeignKey('rel_content_type', 'rel_object_id')

    external_object_id = models.CharField(max_length=255, blank=True, null=True)
    external_content_type = models.CharField(max_length=255, blank=True, null=True)

    objects = models.Manager()
    public = PublicCommentManager()

    metadata = GenericRelation('vitrina_structure.Metadata')

    class Meta:
        db_table = 'comment'
        ordering = ('-created',)
        get_latest_by = 'created'

    def __str__(self):
        return self.get_type_display()

    def get_absolute_url(self):
        if self.content_object:
            return self.content_object.get_absolute_url()
        elif self.rel_content_object:
            return self.rel_content_object.get_absolute_url()
        else:
            return None

    def descendants(self, include_self=False, permission=False):
        descendants = []
        children = Comment.objects.filter(parent_id=self.pk).order_by('created')
        if not permission:
            children = children.filter(is_public=True)
        if include_self:
            descendants.append(self)
        for child in children:
            descendants.extend(child.descendants(include_self=True, permission=permission))
        return descendants

    def can_reply(self):
        if self.type == self.REQUEST:
            return False
        return True

    def body_text(self):
        if self.type == self.REQUEST and self.rel_content_object:
            body_text = _(
                f"Pateiktas naujas prašymas {self.rel_content_object.title}. "
                f"{self.rel_content_object.description}")
        elif self.type == self.PROJECT and self.rel_content_object:
            body_text = _(
                "Šis duomenų rinkinys įtrauktas į "
                f"{self.rel_content_object.get_title()} projektą."
            )
        elif self.type == self.STATUS:
            if isinstance(self.content_object, Request) and self.status == self.OPENED:
                body_text = _(f"Statusas pakeistas į {Request.FILTER_STATUSES.get(Request.OPENED)}.")
            elif isinstance(self.content_object, Request) and self.status == self.PLANNED:
                body_text = _(f"Statusas pakeistas į {Request.FILTER_STATUSES.get(Request.PLANNED)}.")
            else:
                body_text = _(f"Statusas pakeistas į {self.get_status_display()}.")
            if self.body:
                body_text = f"{body_text}\n{self.body}"
        elif self.type == self.PLAN and self.rel_content_object:
            body_text = mark_safe(
                f'Įtraukta į planą '
                f'<a href="{self.rel_content_object.get_absolute_url()}">{self.rel_content_object}</a>'
            )
        else:
            body_text = self.body
        return body_text

    @staticmethod
    def get_statuses():
        statuses = {}
        for status in Comment.STATUSES:
            statuses[status[0]] = status[1]
        return statuses

    def is_error(self):
        return self.type == self.STRUCTURE_ERROR


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
