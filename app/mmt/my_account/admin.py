from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from mmt.projects.models import Project

from .models import Profile, Tag, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    def project_link(self, obj):
        count = Project.objects.filter(user=obj).count()
        url = (
            reverse("admin:projects_project_changelist") + f"?user__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{} ({})</a>', url, _("View projects"), count)

    project_link.short_description = _("Projects")
    readonly_fields = UserAdmin.readonly_fields + ("project_link",)

    autocomplete_fields = ("tags",)

    fieldsets = UserAdmin.fieldsets + (
        (
            _("Related Data"),
            {
                "fields": ("tags", "project_link"),
            },
        ),
    )

    list_display = [
        "username",
        "email",
        "is_active",
        "profile__full_name",
        "profile__locale",
        "project_link",
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
