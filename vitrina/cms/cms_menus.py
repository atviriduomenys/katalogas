from menus.base import Menu, NavigationNode
from menus.menu_pool import menu_pool
from django.utils.translation import gettext_lazy as _


class VitrinaMenu(Menu):

    def get_nodes(self, request):
        return [
            NavigationNode(_('Datasets'), '/datasets/', 1),
            NavigationNode(_('Requests'), '/requests/submitted/', 1),
        ]


menu_pool.register_menu(VitrinaMenu)
