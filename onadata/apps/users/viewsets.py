import json

from channels import Group as ChannelGroup
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.db.models import Q
from registration import signals
from registration.models import RegistrationProfile
from registration.views import RegistrationView
from rest_framework import viewsets
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import detail_route
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_page
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import views

from onadata.apps.api.viewsets.xform_viewset import CsrfExemptSessionAuthentication
from onadata.apps.eventlog.models import FieldSightLog
from onadata.apps.fieldsight.mixins import USURPERS
from onadata.apps.fieldsight.models import BluePrints, Region, Site
from onadata.apps.userrole.models import UserRole
from onadata.apps.userrole.serializers.UserRoleSerializer import MySiteRolesSerializer, MyProjectRolesSerializer, \
    MySiteOnlyRolesSerializer, MySiteRolesSerializerFilteredMA
from onadata.apps.users.models import User, UserProfile
from onadata.apps.users.serializers import UserSerializer, UserSerializerProfile, SearchableUserSerializer

SAFE_METHODS = ('GET', 'POST')

from itertools import chain


class MySitesResultsSetPagination(PageNumberPagination):
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 1000


class MySitesOnlyResultsSetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 1000

class ExtremeLargeJsonResultsSetPagination(PageNumberPagination):
    page_size = 1500
    page_size_query_param = 'page_size'
    max_page_size = 1500


class AddPeoplePermission(BasePermission):

    def has_object_permission(self, request, view, obj):

        if request.role.group.name == "Super Admin":
            return True
        # elif request.role.group.name == "Organization Admin":
        #     return obj.user.organization == request.role.organization
        # elif request.role.group.name == "Project Manager":
        #     return not UserRole.objects.filter(user=obj.user, group_name__in=USURPERS["Project"]).exists()
        # elif
        #
        #     return False
        #     return obj.user == request.user
        # return request.role.organization == obj.organization
        return request.role.group.name in USURPERS['Reviewer']


class SuperAdminPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.role.group.name == "Super Admin"


class EditProfilePermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user == obj.user:
            return True

        elif request.role.group.name == "Super Admin":
            return True

        elif request.role.group.name == "Organization Admin":
            return obj.organization == request.role.organization
        elif request.role.group.name == "Project Manager":
            if UserRole.objects.filter(user=obj.user, group_name__in=USURPERS["Project"]).exists():
                return False
            return obj.user_profile.organization == request.role.organization
        elif request.role.group.name == "Reviewer":
            if UserRole.objects.filter(user=obj.user, group_name__in=USURPERS["Reviewer"]).exists():
                return False
            return obj.user == request.user
        return False


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, AddPeoplePermission)

    def filter_queryset(self, queryset):
        try:
            pk = self.kwargs.get('pk', None)
            queryset = queryset.filter(user_profile__organization__id=pk)
        except:
            queryset = []
        return queryset

    def perform_create(self, serializer):
        data = self.request.data

        if "id" in data and data.get('id'):
            raise ValidationError({
                "Update User Invalid Operation ",
            })

        if "password" not in data:
            raise ValidationError({
                "Password Required ",
            })
        if "cpassword" not in data:
            raise ValidationError({
                "Password Required ",
            })

        if data.get('cpassword') != data.get('password'):
            raise ValidationError({
                "Password Missmatch ",
            })
        username = data.get('username')
        email = data.get('email')
        if User.objects.filter(username=username).exists():
            raise ValidationError({
                "Username Already Used ",
            })
        if User.objects.filter(email=email).exists():
            raise ValidationError({
                "Email Already Used ",
            })
        try:
            with transaction.atomic():
                user = serializer.save()
                user.set_password(data.get('password'))
                user.is_superuser = True
                user.save()
                profile = UserProfile(user=user, organization_id=self.kwargs.get('pk'))
                profile.save()
                site = get_current_site(self.request)

                new_user = RegistrationProfile.objects.create_inactive_user(
                    new_user=user,
                    site=site,
                    send_email=True,
                    request=self.request,
                )
                noti = profile.logs.create(source=self.request.user, type=0, title="new User",
                                    organization=profile.organization, description="new user {0} created by {1}".
                                    format(user.username, self.request.user.username))
                result = {}
                result['description'] = 'new user {0} created by {1}'.format(user.username, self.request.user.username)
                result['url'] = noti.get_absolute_url()
                ChannelGroup("notify-{}".format(profile.organization.id)).send({"text":json.dumps(result)})
                ChannelGroup("notify-0".format(profile.organization.id)).send({"text":json.dumps(result)})

                signals.user_registered.send(sender=RegistrationView, user=new_user, request=self.request)
        except Exception as e:

            raise ValidationError({
                "User Creation Failed {}".format(str(e)),
            })


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserSerializerProfile
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    permission_classes = (IsAuthenticated, EditProfilePermission)
    parser_classes = (FormParser, MultiPartParser)

    def retrieve(self, request, pk=None):
        queryset = UserProfile.objects.all()
        if pk is not None:
            profile = get_object_or_404(queryset, pk=pk)
        else:
            profile = UserProfile.objects.get(user=request.user)
        serializer = UserSerializerProfile(profile)
        return Response(serializer.data)

    def get_serializer_context(self):
        return {'request': self.request}


class UserListViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(pk__gt=0)
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, AddPeoplePermission)

    def filter_queryset(self, queryset):
        try:
            pk = self.kwargs.get('pk', None)
            queryset = queryset.filter(user_profile__organization__id=pk)
        except:
            queryset = []
        return queryset


class SearchableUserListViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(pk__gt=0).distinct('username')
    serializer_class = SearchableUserSerializer
    permission_classes = (IsAuthenticated, SuperAdminPermission)

    def filter_queryset(self, queryset):
        try:
            level = self.kwargs.get('level', None)
            name = self.kwargs.get('username', None)
            if name:
                queryset = queryset.filter(Q(first_name__contains=name)|Q(last_name__contains=name) |Q(username__contains=name))
            if level and level =='1':
                queryset = queryset.filter(user_roles__group__name="Organization Admin")
            if level and level =='2':
                queryset = queryset.filter(user_roles__group__name="Project Manager")
            if level and level =='3':
                queryset = queryset.filter(user_roles__group__name="Reviewer")
            if level and level =='4':
                queryset = queryset.filter(user_roles__group__name="Site Supervisor")
        except:
            queryset = []
        return queryset


class MySitesViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = MySiteRolesSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserRole.objects.filter(ended_at=None, group__name__in=["Site Supervisor", "Region Supervisor"])
    pagination_class = MySitesResultsSetPagination

    def get_queryset(self):
        sites = Site.objects.filter(site_roles__user=self.request.user, site_roles__ended_at=None, id__isnull=False, is_active=True, site_roles__group__name="Site Supervisor")\
            .select_related('region', 'project', 'type', 'project__type', 'project__organization')
        # if self.queryset.filter(user=self.request.user, ended_at=None, region__isnull=False, region__is_active=True,
        #                      group__name="Region Supervisor").values_list('region', flat=True).exists():
        try:
            regions_id = self.queryset.filter(user=self.request.user, ended_at=None, region__isnull=False, region__is_active=True,
                                 group__name="Region Supervisor").values_list('region', flat=True)

            # assume maximum recursion depth is 3
            region_sites = Site.objects.filter(
                Q(region_id__in=regions_id) | Q(region_id__parent__in=regions_id) | Q(region_id__parent__parent__in=regions_id)).select_related('region', 'project', 'type', 'project__type', 'project__organization')
            sites = list(chain(sites, region_sites))
        except:
            pass

        return sites

    def get_serializer_context(self):

        sites = Site.objects.filter(site_roles__user=self.request.user, site_roles__ended_at=None, id__isnull=False,
                                    is_active=True, site_roles__group__name="Site Supervisor") \
            .select_related('region', 'project', 'type', 'project__type', 'project__organization')
        if self.queryset.filter(user=self.request.user, ended_at=None, region__isnull=False, region__is_active=True,
                             group__name="Region Supervisor").values_list('region', flat=True).exists():
            regions_id = self.queryset.filter(user=self.request.user, ended_at=None, region__isnull=False, region__is_active=True,
                                 group__name="Region Supervisor").values_list('region', flat=True)

            # assume maximum recursion depth is 3
            region_sites = Site.objects.filter(
                Q(region_id__in=regions_id) | Q(region_id__parent__in=regions_id) | Q(region_id__parent__parent__in=regions_id)).select_related('region', 'project', 'type', 'project__type', 'project__organization')
            sites = list(chain(sites, region_sites))

        blue_prints = BluePrints.objects.filter(site__in=sites)
        return {'request': self.request, 'blue_prints': blue_prints}



class MySitesViewsetV2(viewsets.ReadOnlyModelViewSet):
    serializer_class = MySiteRolesSerializerFilteredMA
    permission_classes = (IsAuthenticated,)
    renderer_classes = [JSONRenderer]
    queryset = UserRole.objects.filter(ended_at=None, group__name__in=["Site Supervisor", "Region Supervisor"])
    pagination_class = ExtremeLargeJsonResultsSetPagination

    @method_decorator(cache_page(7 * 24 * 60 * 60 ))
    @method_decorator(vary_on_cookie)
    def list(self, request, *args, **kwargs):
        return super(MySitesViewsetV2, self).list(request, *args, **kwargs)

    def get_queryset(self):
        sites = Site.objects.filter(site_roles__user=self.request.user, site_roles__ended_at=None, id__isnull=False, is_active=True, site_roles__group__name="Site Supervisor")\
            .select_related('region', 'project', 'type', 'project__type', 'project__organization')
        # if self.queryset.filter(user=self.request.user, ended_at=None, region__isnull=False, region__is_active=True,
        #                      group__name="Region Supervisor").values_list('region', flat=True).exists():
        try:
            regions_id = self.queryset.filter(user=self.request.user, ended_at=None, region__isnull=False, region__is_active=True,
                                 group__name="Region Supervisor").values_list('region', flat=True)

            # assume maximum recursion depth is 3
            region_sites = Site.objects.filter(
                Q(region_id__in=regions_id) | Q(region_id__parent__in=regions_id) | Q(region_id__parent__parent__in=regions_id)).select_related('region', 'project', 'type', 'project__type', 'project__organization')
            sites = list(chain(sites, region_sites))
        except:
            pass

        return sites

    def get_serializer_context(self):

        sites = Site.objects.filter(site_roles__user=self.request.user, site_roles__ended_at=None, id__isnull=False,
                                    is_active=True, site_roles__group__name="Site Supervisor") \
            .select_related('region', 'project', 'type', 'project__type', 'project__organization')
        if self.queryset.filter(user=self.request.user, ended_at=None, region__isnull=False, region__is_active=True,
                             group__name="Region Supervisor").values_list('region', flat=True).exists():
            regions_id = self.queryset.filter(user=self.request.user, ended_at=None, region__isnull=False, region__is_active=True,
                                 group__name="Region Supervisor").values_list('region', flat=True)

            # assume maximum recursion depth is 3
            region_sites = Site.objects.filter(
                Q(region_id__in=regions_id) | Q(region_id__parent__in=regions_id) | Q(region_id__parent__parent__in=regions_id)).select_related('region', 'project', 'type', 'project__type', 'project__organization')
            sites = list(chain(sites, region_sites))

        blue_prints = BluePrints.objects.filter(site__in=sites)
        return {'request': self.request, 'blue_prints': blue_prints}


class MyRolesViewset(views.APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        regions_id = UserRole.objects.filter(user=self.request.user, ended_at=None, region__isnull=False,
                                          region__is_active=True, group__name="Region Supervisor").values_list('region', flat=True)
        has_regions = UserRole.objects.filter(user=self.request.user, ended_at=None, region__isnull=False,
                                region__is_active=True, group__name="Region Supervisor").values_list('region',

                                                                                                     flat=True).exists()
        myroles = [
            {"user": self.request.user.username,
             "regions": regions_id,
             "has_regions": has_regions

             }

        ]
        return Response(myroles)


class SitesViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = MySiteRolesSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserRole.objects.filter(ended_at=None, group__name="Site Supervisor")
    pagination_class = MySitesResultsSetPagination

    def get_queryset(self):
        sites = Site.objects.filter(site_roles__user=self.request.user, site_roles__ended_at=None, id__isnull=False, is_active=True, site_roles__group__name="Site Supervisor")\
            .select_related('region', 'project', 'type', 'project__type', 'project__organization')

        return sites

    def get_serializer_context(self):

        sites = UserRole.objects.filter(user=self.request.user).values_list('site', flat=True).distinct()

        blue_prints = BluePrints.objects.filter(site__in=sites)
        return {'request': self.request, 'blue_prints': blue_prints}


class MyRegionSitesViewset(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = MySiteRolesSerializer
    queryset = UserRole.objects.filter(ended_at=None, group__name="Region Supervisor")
    pagination_class = MySitesResultsSetPagination

    def get_queryset(self):
        region_id = int(self.request.query_params.get('region_id'))

        sites = Site.objects.filter(Q(region_id=region_id) | Q(region_id__parent=region_id) | Q(region_id__parent__parent=region_id)).select_related('region', 'project', 'type', 'project__type', 'project__organization')

        return sites

    def get_serializer_context(self):
        region_id = int(self.request.query_params.get('region_id'))
        sites = Site.objects.filter(Q(region_id=region_id) | Q(region_id__parent=region_id) | Q(
            region_id__parent__parent=region_id)).select_related('region', 'project', 'type', 'project__type',
                                                                     'project__organization')

        blue_prints = BluePrints.objects.filter(site__in=sites)
        return {'request': self.request, 'blue_prints': blue_prints}
#no project info


class MySitesOnlyViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = MySiteOnlyRolesSerializer
    queryset = UserRole.objects.filter(ended_at=None, group__name="Site Supervisor", site__isnull=False)
    pagination_class = MySitesOnlyResultsSetPagination

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, ended_at=None, site__isnull=False, site__is_active=True, group__name="Site Supervisor").select_related( 'site', 'site__type')

class MyProjectsViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = MyProjectRolesSerializer
    queryset = UserRole.objects.filter(ended_at=None, group__name="Site Supervisor", site__isnull=False)
    # pagination_class = MySitesResultsSetPagination

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, ended_at=None, site__isnull=False, site__is_active=True, group__name="Site Supervisor").distinct('project').select_related( 'project', 'project__type', 'project__organization')

    # def get_serializer_context(self):
    #     # sites = UserRole.objects.filter(user=self.request.user).values_list('site', flat=True).distinct()
    #     # blue_prints = BluePrints.objects.filter(site__in=sites)
    #     return {'request': self.request, 'blue_prints': []}