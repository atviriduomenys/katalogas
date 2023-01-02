from cms.models import CMSPlugin
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext as _

from vitrina.cms.models import LearningMaterial, Faq, ExternalSite
from vitrina.orgs.models import PublishedReport


@plugin_pool.register_plugin
class SideMenuPlugin(CMSPluginBase):
    model = CMSPlugin
    module = _("ADP")
    name = _("Šoninis meniu")
    render_template = "pages/side_menu.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        if instance.page.node.get_children():
            parent = instance.page.node
            children = instance.page.node.get_children()
        else:
            parent = instance.page.node.get_parent()
            children = instance.page.node.get_siblings()
        context.update({
            'children': children,
            'parent': parent
        })
        return context


@plugin_pool.register_plugin
class LearningMaterialPlugin(CMSPluginBase):
    model = CMSPlugin
    module = _("ADP")
    name = _("Mokymosi medžiagos")
    render_template = "pages/learning_material.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update({
            'items': LearningMaterial.objects.filter(
                published__isnull=False
            ).order_by('-published'),
        })
        return context


@plugin_pool.register_plugin
class ReportPlugin(CMSPluginBase):
    model = CMSPlugin
    module = _("ADP")
    name = _("Ataskaitos")
    render_template = "pages/report.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update({
            'items': PublishedReport.objects.all()
        })
        return context


@plugin_pool.register_plugin
class EUCommissionPortalPlugin(CMSPluginBase):
    model = CMSPlugin
    module = _("ADP")
    name = _("Europos komisijos portalai")
    render_template = "pages/other.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update({
            'title': _("Europos komisijos portalai"),
            'items': ExternalSite.objects.filter(type=ExternalSite.EU_COMISSION_PORTAL),
        })
        return context


@plugin_pool.register_plugin
class EULandPlugin(CMSPluginBase):
    model = CMSPlugin
    module = _("ADP")
    name = _("EU šalys")
    render_template = "pages/other.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update({
            'title': _("EU šalys"),
            'items': ExternalSite.objects.filter(type=ExternalSite.EU_LAND),
        })
        return context


@plugin_pool.register_plugin
class OtherLandPlugin(CMSPluginBase):
    model = CMSPlugin
    module = _("ADP")
    name = _("Kitos šalys")
    render_template = "pages/other.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update({
            'title': _("Kitos šalys"),
            'items': ExternalSite.objects.filter(type=ExternalSite.OTHER_LAND),
        })
        return context


@plugin_pool.register_plugin
class FaqPlugin(CMSPluginBase):
    model = CMSPlugin
    module = _("ADP")
    name = _("Dažnai užduodami klausimai")
    render_template = "pages/faq.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update({
            'items': Faq.objects.all(),
        })
        return context
