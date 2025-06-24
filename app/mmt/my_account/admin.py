from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from mmt.upload_jobs.models import UploadJob
from .models import User, Profile, Tag


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    def uploadjob_link(self, obj):
        count = UploadJob.objects.filter(user=obj).count()
        url = (
            reverse("admin:upload_jobs_uploadjob_changelist")
            + f"?user__id__exact={obj.id}"
        )
        return format_html(
            '<a href="{}">{} ({})</a>', url, _("View upload jobs"), count
        )

    uploadjob_link.short_description = _("Upload jobs")

    readonly_fields = UserAdmin.readonly_fields + ("uploadjob_link",)

    autocomplete_fields = ("tags",)

    fieldsets = UserAdmin.fieldsets + (
        (
            _("Related Data"),
            {
                "fields": ("tags", "uploadjob_link"),
            },
        ),
    )

    list_display = [
        "username",
        "email",
        "is_active",
        "profile__full_name",
        "profile__locale",
        "uploadjob_link",
    ]
    list_filter = UserAdmin.list_filter + ("tags",)
    inlines = [ProfileInline]
    actions = ["make_active"]

    @admin.action(description=_("Activate selected users"))
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        # TODO: Send email to each user separately.


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "description",
    ]
    search_fields = ("name", "description")
