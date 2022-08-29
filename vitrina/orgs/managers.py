from treebeard.mp_tree import MP_NodeManager


class PublicOrganizationManager(MP_NodeManager):
    def get_queryset(self):
        return super().get_queryset()
