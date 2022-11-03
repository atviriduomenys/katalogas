from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views.generic import DetailView
from itsdangerous import URLSafeSerializer

from vitrina import settings
from vitrina.helpers import get_current_domain
from vitrina.orgs.forms import RepresentativeUpdateForm
from vitrina.orgs.forms import RepresentativeCreateForm
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.users.models import User
from vitrina.users.views import RegisterView


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
        context_data['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            organization
        )
        return context_data


class OrganizationMembersView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    template_name = 'vitrina/orgs/members.html'
    context_object_name = 'members'
    paginate_by = 20

    object: Organization

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Organization, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )

    def get_queryset(self):
        return (
            Representative.objects.
            filter(
                content_type=ContentType.objects.get_for_model(Organization),
                object_id=self.object.pk
            ).
            order_by("role", "first_name", 'last_name')
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['has_permission'] = has_perm(
            self.request.user,
            Action.CREATE,
            Representative,
            self.object,
        )
        context_data['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context_data


class RepresentativeCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Representative
    form_class = RepresentativeCreateForm
    template_name = 'base_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object_id'] = self.kwargs.get('object_id')
        return kwargs

    def get_success_url(self):
        return reverse('organization-members', kwargs={'pk': self.kwargs.get('organization_id')})

    def has_permission(self):
        organization_id = self.kwargs.get('organization_id')
        organization = get_object_or_404(Organization, pk=organization_id)
        return has_perm(self.request.user, Action.CREATE, Representative, organization)

    def form_valid(self, form):
        self.object: Representative = form.save(commit=False)
        organization_id = self.kwargs.get('organization_id')
        organization = get_object_or_404(Organization, pk=organization_id)
        self.object.object_id = organization_id
        self.object.content_type = ContentType.objects.get_for_model(organization)
        try:
            user = User.objects.get(email=self.object.email)
        except ObjectDoesNotExist:
            user = None
        if user:
            self.object.user = user
            self.object.save()
        else:
            self.object.save()
            serializer = URLSafeSerializer(settings.SECRET_KEY)
            token = serializer.dumps({"representative_id": self.object.pk})
            url = "%s%s" % (
                get_current_domain(self.request),
                reverse('representative-register', kwargs={'token': token})
            )
            send_mail(
                subject=_('Kvietimas prisijungti prie atvirų duomenų portalo'),
                message=_(
                    f'Buvote įtraukti į „{organization}“ organizacijos '
                    'narių sąrašo, tačiau nesate registruotas Lietuvos '
                    'atvirų duomenų portale. Prašome sekite šia nuoroda, '
                    'kad užsiregistruotumėte ir patvirtintumėte savo narystę '
                    'organizacijoje:\n'
                    '\n'
                    f'{url}\n'
                    '\n'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.object.email],
            )
            messages.info(self.request, _("Naudotojui išsiųstas laiškas dėl registracijos"))
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class RepresentativeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Representative
    form_class = RepresentativeUpdateForm
    template_name = 'base_form.html'

    def has_permission(self):
        representative = get_object_or_404(Representative, pk=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.UPDATE, representative)

    def get_success_url(self):
        return reverse('organization-members', kwargs={'pk': self.kwargs.get('organization_id')})


class RepresentativeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Representative
    template_name = 'confirm_delete.html'

    def has_permission(self):
        representative = get_object_or_404(Representative, pk=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.DELETE, representative)

    def get_success_url(self):
        return reverse('organization-members', kwargs={'pk': self.kwargs.get('organization_id')})


class RepresentativeRegisterView(RegisterView):
    def save(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            token = self.kwargs.get('token')
            serializer = URLSafeSerializer(settings.SECRET_KEY)
            data = serializer.loads(token)
            try:
                representative = Representative.objects.get(pk=data.get('representative_id'))
            except ObjectDoesNotExist:
                representative = None
            if representative:
                representative.user = user
                representative.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
        return render(request=request, template_name=self.template_name, context={"form": form})
