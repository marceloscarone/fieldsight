from __future__ import unicode_literals
import json
import datetime
import os, tempfile
from django.contrib.gis.db.models import PointField
from django.contrib.gis.db.models import GeoManager
from django.contrib.contenttypes.fields import GenericRelation
from django.core.urlresolvers import reverse
from django.db import models
from django.conf import settings
from django.db.models import IntegerField, Count, Case, When, Sum
from django.db.models.signals import post_save
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.text import slugify
from jsonfield import JSONField
from .static_lists import COUNTRIES
from django.contrib.auth.models import Group
from django.dispatch import receiver

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.serializers import serialize

from django.db.models import Q


class TimeZone(models.Model):
    time_zone = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    country_code = models.CharField(max_length=255, blank=True, null=True)
    offset_time = models.CharField(max_length=255, blank=True, null=False)

    class Meta:
        ordering = ['time_zone']

    def __unicode__(self):
        return self.time_zone + " - " + self.country


class ExtraUserDetail(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name='extra_details')
    data = JSONField(default={})

    def __unicode__(self):
        return '{}\'s data: {}'.format(self.user.__unicode__(),
                                       repr(self.data))


def create_extra_user_details(sender, instance, created, **kwargs):
    if created:
        ExtraUserDetail.objects.get_or_create(user=instance)


post_save.connect(create_extra_user_details, sender=settings.AUTH_USER_MODEL)


class OrganizationType(models.Model):
    name = models.CharField("Organization Type", max_length=256)

    def __unicode__(self):
        return u'{}'.format(self.name)


class ProjectType(models.Model):
    name = models.CharField("Project Type", max_length=256)

    def __unicode__(self):
        return u'{}'.format(self.name)


class Organization(models.Model):
    name = models.CharField("Organization Name", max_length=255)
    type = models.ForeignKey(
        OrganizationType, verbose_name='Type of Organization', on_delete=models.SET_NULL, blank=True, null=True)
    phone = models.CharField(
        "Contact Number", max_length=255, blank=True, null=True)
    fax = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    country = models.CharField(max_length=3, choices=COUNTRIES, default=u'NPL')
    address = models.TextField(blank=True, null=True)
    public_desc = models.TextField("Public Description", blank=True, null=True)
    additional_desc = models.TextField(
        "Additional Description", blank=True, null=True)
    logo = models.ImageField(
        upload_to="logo", default="logo/default_org_image.jpg")
    is_active = models.BooleanField(default=True)
    location = PointField(geography=True, srid=4326, blank=True, null=True,)
    date_created = models.DateTimeField(auto_now_add=True, blank=True)
    logs = GenericRelation('eventlog.FieldSightLog')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="organizations", null=True, blank=True)

    class Meta:
        ordering = ['-is_active', 'name', ]

    def __unicode__(self):
        return u'{}'.format(self.name)

    objects = GeoManager()

    @property
    def latitude(self):
        if self.location:
            return self.location.y

    @property
    def longitude(self):
        if self.location:
            return self.location.x

    def getname(self):
        return self.name

    @property
    def status(self):
        if self.organization_instances.filter(form_status=1).count():
            return 1
        elif self.organization_instances.filter(form_status=2).count():
            return 2
        elif self.organization_instances.filter(form_status=0).count():
            return 0
        elif self.organization_instances.filter(form_status=3).count():
            return 3
        return 4

    def get_organization_submission(self):
        instances = self.organization_instances.all().order_by('-date')
        outstanding, flagged, approved, rejected = [], [], [], []
        for submission in instances:
            if submission.form_status == 0:
                outstanding.append(submission)
            elif submission.form_status == 1:
                rejected.append(submission)
            elif submission.form_status == 2:
                flagged.append(submission)
            elif submission.form_status == 3:
                approved.append(submission)

        return outstanding, flagged, approved, rejected

    def get_submissions_count(self):
        from onadata.apps.fsforms.models import FInstance
        outstanding = FInstance.objects.filter(
            project__organization=self, project__is_active=True, form_status=0).count()
        rejected = FInstance.objects.filter(
            project__organization=self, project__is_active=True, form_status=1).count()
        flagged = FInstance.objects.filter(
            project__organization=self, project__is_active=True, form_status=2).count()
        approved = FInstance.objects.filter(
            project__organization=self, project__is_active=True, form_status=3).count()

        return outstanding, flagged, approved, rejected

    def get_submissions_count_by_date(self, start_date):
        from onadata.apps.fsforms.models import FInstance
        outstanding = FInstance.objects.filter(
            project__organization=self, project__is_active=True, form_status=0, date__range=[start_date, datetime.datetime.now()]).count()
        rejected = FInstance.objects.filter(
            project__organization=self, project__is_active=True, form_status=1, date__range=[start_date, datetime.datetime.now()]).count()
        flagged = FInstance.objects.filter(
            project__organization=self, project__is_active=True, form_status=2, date__range=[start_date, datetime.datetime.now()]).count()
        approved = FInstance.objects.filter(
            project__organization=self, project__is_active=True, form_status=3, date__range=[start_date, datetime.datetime.now()]).count()

        return outstanding, flagged, approved, rejected

    def get_absolute_url(self):
        return reverse('fieldsight:organizations-dashboard',
                       kwargs={'pk': self.pk})

    @property
    def get_staffs(self):
        staffs = self.organization_roles.filter(
            group__name="Organization Admin"
        ).values_list('id', 'user__username')
        return staffs

    @property
    def get_staffs_org(self):
        staffs = self.organization_roles.filter(
            group__name="Organization Admin")
        return staffs

    @property
    def get_staffs_id(self):
        return self.organization_roles.filter(
            group__name="Organization Admin"
        ).values_list('id', flat=True)

    def get_organization_type(self):
        return self.type.name

class ProjectAllManager(models.Manager):
    def get_queryset(self):
        return super(ProjectAllManager, self).get_queryset().all()

class ProjectManager(GeoManager):
    def get_queryset(self):
        return super(ProjectManager, self).get_queryset().filter(is_active=True)

class Project(models.Model):
    name = models.CharField(max_length=255)
    type = models.ForeignKey(ProjectType, verbose_name='Type of Project')
    phone = models.CharField(max_length=255, blank=True, null=True)
    fax = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    donor = models.CharField(max_length=256, blank=True, null=True)
    public_desc = models.TextField("Public Description", blank=True, null=True)
    additional_desc = models.TextField(
        "Additional Description", blank=True, null=True)
    organization = models.ForeignKey(Organization, related_name='projects')
    logo = models.ImageField(
        upload_to="logo", default="logo/default_project_image.jpg")
    is_active = models.BooleanField(default=True)
    location = PointField(geography=True, srid=4326, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True, blank=True)
    cluster_sites = models.BooleanField(default=False)
    site_meta_attributes = JSONField(default=list)
    gsuit_meta = JSONField(default={})
    # gsuit_meta sample = {'site_progress':{'link':'', 'last_updated':''}}
    logs = GenericRelation('eventlog.FieldSightLog')
    all_objects = ProjectAllManager()
    objects = ProjectManager()
    
    geo_layers = models.ManyToManyField('geo.GeoLayer', blank=True)

    class Meta:
        ordering = ['-is_active', 'name', ]

    @property
    def latitude(self):
        if self.location:
            return self.location.y

    @property
    def longitude(self):
        if self.location:
            return self.location.x

    def getname(self):
        return self.name

    def __unicode__(self):
        return u'{}'.format(self.name)

    @property
    def get_staffs(self):
        staffs = self.project_roles.filter(
            group__name__in=["Reviewer", "Project Manager"])
        return staffs

    @property
    def get_staffs_both_role(self):
        managers_id = self.project_roles.filter(
            group__name="Project Manager").values_list('user__id', flat=True)
        reviewers_id = self.project_roles.filter(
            group__name="Reviewer").values_list('user__id', flat=True)
        both = list(set(managers_id).intersection(reviewers_id))
        return both

    def get_organization_name(self):
        return self.organization.name

    def get_project_type(self):
        return self.type.name

    @property
    def status(self):
        if self.project_instances.filter(form_status=1).count():
            return 1
        elif self.project_instances.filter(form_status=2).count():
            return 2
        elif self.project_instances.filter(form_status=0).count():
            return 0
        elif self.project_instances.filter(form_status=3).count():
            return 3
        return 4

    def get_project_submission(self):
        instances = self.project_instances.all().order_by('-date')
        outstanding, flagged, approved, rejected = [], [], [], []
        for submission in instances:
            if submission.form_status == 0:
                outstanding.append(submission)
            elif submission.form_status == 1:
                rejected.append(submission)
            elif submission.form_status == 2:
                flagged.append(submission)
            elif submission.form_status == 3:
                approved.append(submission)

        return outstanding, flagged, approved, rejected

    def get_submissions_count(self):
        qs = self.project_instances.aggregate(
            outstanding=Count(Case(When(form_status=0, project=self, then=1), output_field=IntegerField(),)),
            flagged=Count(Case(When(form_status=2, project=self, then=1), output_field=IntegerField(),)),
            approved=Count(Case(When(form_status=3, project=self, then=1), output_field=IntegerField(),)),
            rejected=Count(Case(When(form_status=1, project=self, then=1), output_field=IntegerField(),)),
        )
        return qs.get('outstanding', 0), qs.get('flagged', 0), qs.get('approved', 0), qs.get('rejected', 0)

    def get_absolute_url(self):
        return reverse('fieldsight:project-dashboard', kwargs={'pk': self.pk})


class Region(models.Model):
    identifier = models.CharField(max_length=255)
    parent = models.ForeignKey('Region', blank=True, null=True, default=None, related_name="children")
    name = models.CharField(max_length=255, null=True, blank=True,)
    project = models.ForeignKey(Project, related_name="project_region")
    date_created = models.DateTimeField(auto_now_add=True, blank=True)
    date_updated = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    logs = GenericRelation('eventlog.FieldSightLog')

    class Meta:
        unique_together = [('identifier', 'project'), ]

    # def get_sites_count(self):
    #
    #     site_count = self.regions.all().count()
    #     if self.children.all().count() > 0:
    #         sub_site_count = 0
    #         for child in self.children.all():
    #             sub_site_count += child.get_sites_count()
    #         return sub_site_count + site_count
    #     else:
    #         return site_count

    def getname(self):
        return self.name or self.identifier

    def get_absolute_url(self):
        return reverse('fieldsight:regional-sites', kwargs={'pk': self.project.pk, 'region_id': self.pk})

    def get_sites_count(self):
        return Site.objects.filter(
            Q(region_id=self.id) | Q(region_id__parent=self.id) | Q(
                region_id__parent__parent=self.id)).select_related('region', 'project', 'type', 'project__type',
                                                                          'project__organization').count()

    def get_sites(self):
        return Site.objects.filter(
            Q(region_id=self.id) | Q(region_id__parent=self.id) | Q(
                region_id__parent__parent=self.id)).select_related('region', 'project', 'type', 'project__type',
                                                                   'project__organization').values_list('name', flat=True)

    def get_sites_id(self):
        return Site.objects.filter(
            Q(region_id=self.id) | Q(region_id__parent=self.id) | Q(
                region_id__parent__parent=self.id)).select_related('region', 'project', 'type', 'project__type',
                                                                   'project__organization').values_list('id',
                                                                                                        flat=True)

    def get_concat_identifier(self):       
        return self.identifier + "_"


class SiteType(models.Model):
    identifier = models.IntegerField("ID")
    name = models.CharField("Type", max_length=256)
    project = models.ForeignKey(Project, related_name="types")
    deleted = models.BooleanField(default=False)

    def __unicode__(self):
        return u'{}'.format(self.name)

    class Meta:
        ordering = ['-identifier']
        unique_together = [('identifier', 'project'), ]


class SiteAllManager(models.Manager):
    def get_queryset(self):
        return super(SiteAllManager, self).get_queryset().all()

class SiteManager(GeoManager):
    def get_queryset(self):
        return super(SiteManager, self).get_queryset().filter(is_active=True)


class Site(models.Model):
    identifier = models.CharField("ID", max_length=255)
    name = models.CharField(max_length=255)
    type = models.ForeignKey(SiteType, verbose_name='Type of Site', related_name="sites", null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    public_desc = models.TextField("Public Description", blank=True, null=True)
    additional_desc = models.TextField(
        "Additional Description", blank=True, null=True)
    project = models.ForeignKey(Project, related_name='sites')
    logo = models.ImageField(
        upload_to="logo", default="logo/default_site_image.png")
    is_active = models.BooleanField(default=True)
    location = PointField(geography=True, srid=4326, blank=True, null=True)
    is_survey = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True, blank=True)
    region = models.ForeignKey(
        Region, related_name='regions', blank=True, null=True)
    site_meta_attributes_ans = JSONField(default=dict)
    current_progress = models.IntegerField(default=0)
    current_status = models.IntegerField(default=0)
    all_objects = SiteAllManager()
    objects = SiteManager()
    
    logs = GenericRelation('eventlog.FieldSightLog')

    class Meta:
        ordering = ['-is_active', '-id']
        unique_together = [('identifier', 'project', 'is_active'), ]

    @property
    def latitude(self):
        if self.location:
            return self.location.y

    @property
    def longitude(self):
        if self.location:
            return self.location.x

    def update_status(self):
        try:
            status = self.site_instances.order_by('-date').first().form_status
        except:
            status = 0
        self.current_status = status
        self.save()

    def getname(self):
        return self.name

    def __unicode__(self):
        return u'{}'.format(self.name)

    @property
    def get_supervisors(self):
        return self.site_roles.all()

    @property
    def get_supervisor_id(self):
        staffs = list(self.site_roles.filter(group__name="Site Supervisor"))
        if staffs:
            return [role.user.id for role in staffs]
        return []

    def get_organization_name(self):
        return self.project.organization.name

    def get_project_name(self):
        return self.project.name

    def get_site_type(self):
        return self.type.name

    def update_current_progress(self):
        self.current_progress = self.progress()
        try:
            status = self.site_instances.order_by('-date').first().form_status
        except:
            status = 0
        self.current_status = status
        self.save()

    def progress(self):
        approved_site_forms_weight = self.site_instances.filter(form_status=3, site_fxf__is_staged=True).distinct('site_fxf').values_list('site_fxf__stage__weight', flat=True)
        approved_site_weight_total = sum([w for w in approved_site_forms_weight if w  is not None])
        approved_project_forms_weight = self.site_instances.filter(form_status=3, project_fxf__is_staged=True).distinct('project_fxf').values_list('project_fxf__stage__weight', flat=True)
        approved_projects_weight_total = sum([w for w in approved_project_forms_weight if w is not None])
        approved_weight = approved_site_weight_total + approved_projects_weight_total
        if approved_weight:
            from onadata.apps.fsforms.models import Stage
            site_stages_weight = Stage.objects.filter(stage__site=self).aggregate(Sum('weight'))['weight__sum']
            project_stages_weight = Stage.objects.filter(stage__project=self.project).aggregate(Sum('weight'))['weight__sum']
            site_stages_weight = site_stages_weight if site_stages_weight else 0
            project_stages_weight = project_stages_weight if project_stages_weight else 0
            total_weight = site_stages_weight + project_stages_weight
            p = ("%.0f" % (approved_weight / (total_weight * 0.01)))
            p = int(p)
            if p > 99:
                return 100
            return p
        approved_forms_site = self.site_instances.filter(form_status=3, site_fxf__is_staged=True).values_list('site_fxf', flat=True)
        approved_forms_project = self.site_instances.filter(form_status=3, project_fxf__is_staged=True).values_list('project_fxf', flat=True)
        approved = len(set(approved_forms_site)) + len(set(approved_forms_project))
        if not approved:
            return 0
        from onadata.apps.fsforms.models import Stage
        stages = Stage.objects.filter(stage__project=self.project).count() + Stage.objects.filter(stage__site=self).count()
        if not stages:
            return 0
        p = ("%.0f" % (approved/(stages*0.01)))
        p = int(p)
        if p > 99:
            return 100
        return p

    @property
    def site_progress(self):
        return self.progress()

    @property
    def status(self):
        if self.site_instances.filter(form_status=1).count():
            return 1
        elif self.site_instances.filter(form_status=2).count():
            return 2
        elif self.site_instances.filter(form_status=0).count():
            return 0
        elif self.site_instances.filter(form_status=3).count():
            return 3
        return 4

    @property
    def site_status(self):
        forms = self.project.project_forms.filter(is_staged=True, is_deleted=False, is_deployed=True)
        try:
            return self.site_instances.filter(project_fxf__in=forms).order_by('-instance_id')[0].get_abr_form_status()
        except:
            return "No Submission"

    def get_site_submission(self):
        instances = self.site_instances.all().order_by('-date')
        outstanding, flagged, approved, rejected = [], [], [], []
        for submission in instances:
            if submission.form_status == 0:
               outstanding.append(submission)
            elif submission.form_status == 1:
                rejected.append(submission)
            elif submission.form_status == 2:
                flagged.append(submission)
            elif submission.form_status == 3:
                approved.append(submission)

        return outstanding, flagged, approved, rejected

    def get_site_submission_count(self):
        instances = self.site_instances.all().order_by('-date')
        outstanding, flagged, approved, rejected = 0, 0, 0, 0
        for submission in instances:
            if submission.form_status == 0:
                outstanding += 1
            elif submission.form_status == 1:
                rejected += 1
            elif submission.form_status == 2:
                flagged += 1
            elif submission.form_status == 3:
                approved += 1
        response = {}
        response['outstanding'] = outstanding
        response['rejected'] = rejected
        response['flagged'] = flagged
        response['approved'] = approved

        return response

    def get_absolute_url(self):
        return reverse('fieldsight:site-dashboard', kwargs={'pk': self.pk})


def get_image_filename(instance, filename):
    title = instance.site.identifier
    project = instance.site.project.pk
    slug = slugify(title)
    return "blueprint_images/%s-%s-%s" % (project, slug, filename)


def get_survey_image_filename(instance, filename):
    title = instance.site.identifier
    project = instance.site.project.pk
    slug = slugify(title)
    return "survey_images/%s-%s-%s" % (project, slug, filename)


class BluePrints(models.Model):
    site = models.ForeignKey(Site, related_name="blueprints")
    image = models.FileField(upload_to=get_image_filename,
                             verbose_name='BluePrints',)

    def get_name(self):
        import os
        return os.path.basename(self.image.file.name)


class SiteCreateSurveyImages(models.Model):
    site = models.ForeignKey(Site, related_name="create_surveys")
    image = models.ImageField(upload_to=get_survey_image_filename,
                              verbose_name='survey images',)


class ChatMessage(models.Model):
    message = models.CharField(max_length=255)
    room = models.CharField(max_length=30)

    class Meta:
        db_table = 'chat_message'


class UserInvite(models.Model):
    email = models.CharField(max_length=255)
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='invited_by_user')
    is_used = models.BooleanField(default=False)
    is_declied = models.BooleanField(default=False)
    token = models.CharField(max_length=255)
    group = models.ForeignKey(Group)
    site = models.ManyToManyField(Site, related_name='invite_site_roles')
    project = models.ManyToManyField(Project, related_name='invite_project_roles')
    regions = models.ManyToManyField(Region, related_name='invite_region_roles')
    organization = models.ForeignKey(Organization, related_name='invite_organization_roles')
    logs = GenericRelation('eventlog.FieldSightLog')

    def __unicode__(self):
        return self.email + "-----" + str(self.is_used)

    def getname(self):
        return str("invited")
        
    def get_absolute_url(self):
        invite_idb64 = urlsafe_base64_encode(force_bytes(self.pk))
        kwargs = {'invite_idb64': invite_idb64, 'token': self.token}
        return reverse('fieldsight:activate-role', kwargs=kwargs)


class ProjectGeoJSON(models.Model):
    project = models.OneToOneField(Project, related_name="project_geojson")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    geoJSON = models.FileField(max_length=755, blank=True, null=True)

    def generate_new(self):
        data = serialize('full_detail_geojson',
               Site.objects.filter(project_id = self.project.id, is_survey=False, is_active=True),
               geometry_field='location',
               fields=('name', 'location', 'id', 'identifier'))

        with tempfile.NamedTemporaryFile() as temp:
            temp.write(data)
            temp.seek(0)
            if default_storage.exists('geojsonFiles/' + str(self.project.id) + '/site-geojson/sites.geojson'):
                default_storage.delete('geojsonFiles/' + str(self.project.id) + '/site-geojson/sites.geojson')
            
            geojson_url = default_storage.save('geojsonFiles/' + str(self.project.id) + '/site-geojson/sites.geojson', temp)
            self.geoJSON.name = geojson_url
            self.save()


class RequestOrganizationStatus(models.Model):
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='request_organization_by')
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='request_organization_to')
    is_approve = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)
    organization = models.ForeignKey(Organization, related_name='request_org_status')
    # logs = GenericRelation('eventlog.FieldSightLog')
