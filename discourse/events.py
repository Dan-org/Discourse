from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.dispatch import receiver

from models import (comment_manipulate, 
                    attachment_manipulate,
                    attachment_view,
                    document_manipulate)

from notice import subscribe, send_event, get_instance_from_sig


@receiver(comment_manipulate)
def check_author(sender, request, action, **kwargs):
    """
    When a comment is edited, make sure the user is the author or an admin
    """
    if action == 'edit' or action == 'delete':
        if request.user != sender.author and not request.user.is_superuser:
            raise PermissionDenied()


@receiver(attachment_view)
def send_to_aws_for_attachment(sender, request, **kwargs):
    """
    When a user looks for a file, get it on aws.
    """
    from apps.project.models import Network, Studio, Project

    attachment = sender
    file = attachment.file
    storage = file.storage

    obj = get_instance_from_sig(attachment.path)
    if hasattr(obj, 'secure'):
        if obj.secure:
            if not obj.can_see(request):
                raise PermissionDenied()
            storage.secure = obj.secure

    return HttpResponseRedirect( storage.url(file.name) )