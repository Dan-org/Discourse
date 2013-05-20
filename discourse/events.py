from django.core.exceptions import PermissionDenied
from django.dispatch import receiver

from models import (comment_pre_edit, comment_post_edit, 
                    attachment_pre_edit, attachment_post_edit,
                    document_pre_edit, document_post_edit)

from notice import subscribe, event


@receiver(comment_pre_edit)
def check_author(sender, request, action, **kwargs):
    """
    When a comment is edited, make sure the user is the author or an admin
    """
    if action == 'edit' or action == 'delete':
        if request.user != sender.author and not request.user.is_superuser:
            raise PermissionDenied()


@receiver(comment_post_edit)
def subscribe_on_comment(sender, request, action, **kwargs):
    """
    When a user posts a comment, subscribe them to the path.
    """
    if action == 'create':
        event(sender.author, sender.path, "comment", comment=sender)
