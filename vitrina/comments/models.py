from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

from vitrina.comments.managers import PublicCommentManager
from vitrina.requests.models import Request
from vitrina.structure.models import Metadata


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
        (REJECTED, _("Atmestas")),
    )
    COMBINED_STATUSES = tuple(sorted(set(STATUSES + tuple(Request.STATUSES))))

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField(default=1)
    edited_at = models.DateTimeField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    deleted_date = models.DateTimeField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("Comment", blank=True, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey("vitrina_users.User", on_delete=models.CASCADE)
    is_public = models.BooleanField(default=True, verbose_name=_("Viešas komentaras"))
    type = models.CharField(max_length=255, choices=TYPES, default=USER)
    status = models.CharField(max_length=255, blank=True, null=True, choices=COMBINED_STATUSES)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="content_type_comments",
        null=True,
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    rel_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="rel_content_type_comments",
    )
    rel_object_id = models.PositiveIntegerField(blank=True, null=True)
    rel_content_object = GenericForeignKey("rel_content_type", "rel_object_id")

    external_object_id = models.CharField(max_length=255, blank=True, null=True)
    external_content_type = models.CharField(max_length=255, blank=True, null=True)

    objects = models.Manager()
    public = PublicCommentManager()

    metadata = GenericRelation("vitrina_structure.Metadata")

    class Meta:
        db_table = "comment"
        ordering = ("-created",)
        get_latest_by = "created"

    def __str__(self):
        return self.get_type_display()

    def get_absolute_url(self):
        if self.content_object and hasattr(self.content_object, "get_absolute_url"):
            return self.content_object.get_absolute_url()
        elif self.rel_content_object and hasattr(self.rel_content_object, "get_absolute_url"):
            return self.rel_content_object.get_absolute_url()
        else:
            return None

    def descendants(self, include_self=False, permission=False):
        descendants = []
        children = Comment.objects.filter(parent_id=self.pk).order_by("created")
        if not permission:
            children = children.filter(is_public=True)
        if include_self:
            descendants.append(self)
        for child in children:
            descendants.extend(child.descendants(include_self=True, permission=permission))
        return descendants

    def ancestors(self, include_self=False):
        ancestors = []
        if include_self:
            ancestors.append(self)
        if self.parent:
            ancestors.extend(self.parent.ancestors(include_self=True))
        return ancestors

    def can_reply(self):
        if self.type == self.REQUEST:
            return False
        return True

    def body_text(self):
        if self.type == self.REQUEST and self.rel_content_object:
            url = reverse("request-detail", kwargs={"pk": self.rel_content_object.id})
            body_text = _(f"Pateiktas naujas prašymas: **[{self.rel_content_object.title}]({url})**.")
        elif self.type == self.PROJECT and self.rel_content_object:
            body_text = _(f"Šis duomenų rinkinys įtrauktas į {self.rel_content_object.get_title()} projektą.")
        elif self.type == self.PLAN and self.rel_content_object:
            body_text = mark_safe(
                f'Įtraukta į planą <a href="{self.rel_content_object.get_absolute_url()}">{self.rel_content_object}</a>'
            )
        elif self.type == self.STRUCTURE:
            body_text = _("""Struktūros importavimo metu sukurtas sisteminis komentaras.<br>
                <b>Objektas:</b> {content_type} | {content_object}<br>
                <b>Parengimas:</b> <pre><code>{prepare}</code></pre><br>
                <b>Nuoroda:</b> <a href="{uri}">{uri}</a>
            """).format(
                content_type=str(self.content_type).split("|")[-1] if self.content_type else None,
                content_object=self.content_object,
                prepare=escape(self.prepare),
                uri=escape(self.uri),
            )
            return mark_safe(body_text)
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

    def _get_structure_metadata(self) -> Metadata | None:
        return self.metadata.first() if self.type == self.STRUCTURE and self.metadata.exists() else None

    @property
    def prepare(self) -> str | None:
        return meta.prepare if (meta := self._get_structure_metadata()) else None

    @property
    def uri(self) -> str | None:
        return meta.uri if (meta := self._get_structure_metadata()) else None


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
        db_table = "suggestion"
