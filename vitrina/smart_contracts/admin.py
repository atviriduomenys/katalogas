from django.contrib import admin

from vitrina.smart_contracts.models import SmartContractTemplate

from django.utils.translation import gettext_lazy as _


@admin.register(SmartContractTemplate)
class SmartContractTemplateAdmin(admin.ModelAdmin):
    class Meta:
        verbose_name = _("Išmaniųjų sutarčių numatytasis šablonas")
        verbose_name_plural = _("Išmaniųjų sutarčių numatytieji šablonai")
