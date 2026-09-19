from django import template

from mmt.projects.models import ACTIONS

register = template.Library()


@register.simple_tag
def processing_actions():
    """The processing action registry, for templates without an instance.

    ProcessingRequest.actions covers the case where the values are needed as
    well; this tag is for the header row of the request table.
    """
    return ACTIONS
