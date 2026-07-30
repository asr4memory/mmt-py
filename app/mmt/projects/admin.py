from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from mmt.projects.models import ProcessingRequest, Project
from mmt.projects.tasks import send_processing_request_updated_email
from mmt.uploaded_files.admin import UploadedFileDisplayMixin
from mmt.uploaded_files.models import UploadedFile


class UploadedFileInline(UploadedFileDisplayMixin, admin.TabularInline):
    # Mirror UploadedFileAdmin.list_display (minus 'project', which is the
    # parent here). Per-file detail fields live on the change form.
    fields = [
        'filename_display',
        'status',
        'integrity',
        'media_type',
        'size_display',
        'duration_display',
        'created_at',
        'updated_at',
    ]
    readonly_fields = fields
    ordering = ['-created_at']

    model = UploadedFile

    can_delete = True
    extra = 0

    @admin.display(description=_('Filename'))
    def filename_display(self, obj):
        """Like the mixin's column, but linked to the file's detail page.

        The changelist links its first column automatically; a TabularInline
        does not, so build the link explicitly here.
        """
        url = reverse('admin:uploaded_files_uploadedfile_change', args=[obj.pk])
        return format_html(
            '<a href="{}" title="{}">{}</a>',
            url,
            obj.filename,
            Truncator(obj.filename).chars(60),
        )

    def has_add_permission(self, request, obj):
        """Do not show add link."""
        return False


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'created_at']
    list_display_links = ['title']
    list_filter = ['user', 'created_at']
    search_fields = ['title', 'description', 'user__username']
    fields = ['title', 'user', 'description', 'downloadable_files_count']
    readonly_fields = ['user', 'downloadable_files_count']
    inlines = [UploadedFileInline]


@admin.register(ProcessingRequest)
class ProcessingRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'project__user',
        'project',
        'status',
        'created_at',
        'updated_at',
    ]
    list_display_links = ['id']
    list_filter = ['project__user', 'project', 'status', 'created_at', 'updated_at']
    search_fields = ['=id', 'project__user__username', 'description', 'admin_comment']

    fields = [
        'user_link',
        'project',
        'status',
        'created_at',
        'updated_at',
        'description',
        'admin_comment',
        'language',
        'make_available_on_platform',
        'replace_existing_files',
        'check_media_files',
        'transcribe',
        'uploaded_files_count',
        'uploaded_files_list',
    ]
    readonly_fields = [
        'user_link',
        'project',
        'created_at',
        'updated_at',
        'description',
        'language',
        'make_available_on_platform',
        'replace_existing_files',
        'check_media_files',
        'transcribe',
        'uploaded_files_count',
        'uploaded_files_list',
    ]

    def user_link(self, obj):
        user = obj.project.user
        url = reverse('admin:my_account_user_change', args=[user.id])
        return format_html(
            '{} &lt;{}&gt; <a href="{}">{}</a>',
            user.username,
            user.email,
            url,
            _('View user'),
        )

    user_link.short_description = _('User')

    def uploaded_files_list(self, obj):
        sorted_files = sorted(obj.uploaded_files, key=str.lower)

        item = '<li>{}</li>'
        items = item * len(sorted_files)
        all = '<ul style="margin: 0; padding: 0;">' + items + '</ul>'

        return format_html(
            all,
            *sorted_files,
        )

    uploaded_files_list.short_description = _('Uploaded files')

    def save_model(self, request, obj, form, change):
        field = 'status'
        super().save_model(request, obj, form, change)
        if change and field in form.changed_data:
            send_processing_request_updated_email.delay(obj.id)
