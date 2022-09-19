from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic import DetailView

from vitrina import settings
from vitrina.orgs.forms import RepresentativeUpdateForm, RepresentativeCreateForm
from vitrina.orgs.models import Organization, Representative
from vitrina.users.models import User


class OrganizationListView(ListView):
    model = Organization
    template_name = 'vitrina/orgs/list.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        jurisdiction = self.request.GET.get('jurisdiction')
        orgs = Organization.public.all()

        if query:
            orgs = orgs.filter(title__icontains=query)
        if jurisdiction:
            orgs = orgs.filter(jurisdiction=jurisdiction)
        return orgs.order_by("-created")

    def get_context_data(self, **kwargs):
        context = super(OrganizationListView, self).get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()
        query = self.request.GET.get("q", "")
        context['jurisdictions'] = [{
            'title': jurisdiction,
            'query': "?%s%sjurisdiction=%s" % ("q=%s" % query if query else "", "&" if query else "", jurisdiction),
            'count': filtered_queryset.filter(jurisdiction=jurisdiction).count(),
        } for jurisdiction in Organization.public.values_list('jurisdiction', flat="True")
            .distinct().order_by('jurisdiction').exclude(jurisdiction__isnull=True)]
        context['selected_jurisdiction'] = self.request.GET.get('jurisdiction')
        context['jurisdiction_query'] = self.request.GET.get("jurisdiction", "")
        return context


class OrganizationDetailView(DetailView):
    model = Organization
    template_name = 'vitrina/orgs/detail.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        organization: Organization = self.object
        context_data['ancestors'] = organization.get_ancestors()
        return context_data


class OrganizationMembersView(OrganizationDetailView):
    template_name = 'vitrina/orgs/members.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        organization: Organization = self.object
        context_data['members'] = organization.representative_set.all()
        return context_data


class RepresentativeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Representative
    form_class = RepresentativeCreateForm
    template_name = 'base_form.html'

    def has_permission(self):
        return self.request.user.role == Representative.COORDINATOR

    def form_valid(self, form):
        self.object: Representative = form.save(commit=False)
        organization_id = self.kwargs.get('organization_id')
        organization = get_object_or_404(Organization, pk=organization_id)
        self.object.organization = organization
        try:
            user = User.objects.get(email=self.object.email)
            user.organization = organization
            user.role = self.object.role
            user.save()

            self.object.first_name = user.first_name
            self.object.last_name = user.last_name
            self.object.phone = user.phone
        except ObjectDoesNotExist:
            send_mail(
                subject=_('Užsiregistruokite'),
                message=_('Prašome užsiregistruoti adresu https://data.gov.lt/register'),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.object.email],
            )
            messages.info(self.request, _("Naudotojui išsiųstas laiškas dėl registracijos"))
        self.object.save()
        return HttpResponseRedirect(reverse('organization-members', kwargs={'pk': self.kwargs.get('organization_id')}))


class RepresentativeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Representative
    form_class = RepresentativeUpdateForm
    template_name = 'base_form.html'

    def has_permission(self):
        return self.request.user.role == Representative.COORDINATOR

    def get_success_url(self):
        return reverse('organization-members', kwargs={'pk': self.kwargs.get('organization_id')})
