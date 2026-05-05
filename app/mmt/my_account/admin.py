from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import JSONField
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget
from import_export import resources
from import_export.admin import ExportMixin, ImportExportMixin
from import_export.fields import Field

from mmt.my_account.models import Profile, Tag, User
from mmt.my_account.tasks import (
    send_upload_permission_granted_email,
    send_dpa_created_email,
)
from mmt.projects.models import Project


class UserResource(resources.ModelResource):
    full_name = Field(attribute='full_name')
    external = Field(attribute='is_external_user')
    has_dpa_file = Field(attribute='has_dpa_file')

    class Meta:
        model = User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ['full_name', 'locale', 'dpa', 'feature_flags']
    readonly_fields = ['feature_flags']


@admin.register(User)
class CustomUserAdmin(ExportMixin, UserAdmin):
    resource_classes = [UserResource]

    def project_link(self, obj):
        count = Project.objects.filter(user=obj).count()
        url = (
            reverse('admin:projects_project_changelist') + f'?user__id__exact={obj.id}'
        )
        return format_html('<a href="{}">{} ({})</a>', url, _('View projects'), count)

    project_link.short_description = _('Projects')
    readonly_fields = UserAdmin.readonly_fields + (
        'project_link',
        'upload_permission_requested_at',
        'terms_accepted_version',
        'terms_accepted_at',
        'dpa_accepted_at',
    )

    autocomplete_fields = ('tags',)

    fieldsets = (
        UserAdmin.fieldsets[:-1]
        + (
            (
                UserAdmin.fieldsets[-1][0],
                {
                    'fields': (
                        'last_login',
                        'date_joined',
                        'upload_permission_requested_at',
                        'terms_accepted_version',
                        'terms_accepted_at',
                        'dpa_accepted_at',
                    )
                },
            ),
        )
        + (
            (
                _('Related Data'),
                {
                    'fields': ('tags', 'project_link'),
                },
            ),
        )
    )

    @admin.display(description=_('Tags'))
    def get_tags(self, obj):
        return ', '.join([t.name for t in obj.tags.all()])

    list_display = [
        'username',
        'email',
        'is_active',
        'date_joined',
        'profile__full_name',
        'get_tags',
        'project_link',
        'terms_accepted_version',
        'terms_accepted_at',
        'is_external_user',
        'dpa_accepted_at',
        'has_dpa_file',
    ]
    list_filter = UserAdmin.list_filter + ('tags',)
    inlines = [ProfileInline]
    actions = ['make_active']

    @admin.action(description=_('Activate selected users'))
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        # TODO: Send email to each user separately.

    def save_model(self, request, obj, form, change):
        did_not_belong_to_uploaders = not (obj.groups.filter(name='Uploaders').exists())
        does_belong_to_uploaders = (
            form.cleaned_data['groups'].filter(name='Uploaders').exists()
        )
        super().save_model(request, obj, form, change)

        if (
            change
            and ('groups' in form.changed_data)
            and did_not_belong_to_uploaders
            and does_belong_to_uploaders
        ):
            send_upload_permission_granted_email.delay(obj.id)

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)

        for form in formset.forms:
            if not form.instance.pk:
                continue

            if 'dpa' in form.changed_data and bool(form.instance.dpa.name):
                send_dpa_created_email.delay(form.instance.user_id)


@admin.register(Tag)
class TagAdmin(ImportExportMixin, admin.ModelAdmin):
    list_display = [
        'name',
        'description',
    ]
    search_fields = ('name', 'description')
