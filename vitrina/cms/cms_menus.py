from menus.base import Menu, NavigationNode
from menus.menu_pool import menu_pool
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class VitrinaMenu(Menu):

    def get_nodes(self, request):
        return [
            NavigationNode(_('Duomenys'), reverse('dataset-list'), 1),
            NavigationNode(_('Poreikis'), reverse('request-list'), 1),
            NavigationNode(_('Projektai'), reverse('project-list'), 1),
        ]


menu_pool.register_menu(VitrinaMenu)
