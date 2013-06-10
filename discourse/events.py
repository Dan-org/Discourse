from django.core.exceptions import PermissionDenied
from django.dispatch import receiver

from models import (comment_manipulate, 
                    attachment_manipulate,
                    document_manipulate)

from notice import subscribe, send_event


@receiver(comment_manipulate)
def check_author(sender, request, action, **kwargs):
    """
    When a comment is edited, make sure the user is the author or an admin
    """
    if action == 'edit' or action == 'delete':
        if request.user != sender.author and not request.user.is_superuser:
            raise PermissionDenied()


@receiver(comment_manipulate)
def subscribe_on_comment(sender, request, action, **kwargs):
    """
    When a user posts a comment, subscribe them to the path, and
    send an event.
    """
    comment = sender
    if action == 'create':
        subscribe(comment.author, comment.path)
        send_event(comment.author, "comment", comment.path, comment=comment)
