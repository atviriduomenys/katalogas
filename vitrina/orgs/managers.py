from treebeard.al_tree import AL_NodeManager


class PublicOrganizationManager(AL_NodeManager):
    def get_queryset(self):
        return super().get_queryset()
