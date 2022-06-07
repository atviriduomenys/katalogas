from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool


@apphook_pool.register
class VitrinaApphook(CMSApp):
    app_name = 'vitrina'
    name = "Atvirų duomenų portalas"

    def get_urls(self, page=None, language=None, **kwargs):
        return [
            'vitrina.datasets.urls',
        ]
