"""

"""
import json, posixpath
from cleaner import clean_html

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.template.loader import render_to_string
from django.template import RequestContext

from ajax import JsonResponse
from models import Attachment, Document, Comment


### Helpers ###
def render_comment(request, comment):
    return render_to_string('discourse/thread-comment.html', locals(), RequestContext(request))


### Views ###
def thread(request, path):
    """
    On head with path, return info about the comment.
    On delete with path, delete the comment.
    On post with id, edit the comment.
    On post without id, create a new comment.
    On get with id, show the comment.
    On get without id, return a list of comments in the thread.
    """
    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        body = request.POST['body']
        next = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
        if body.strip() == '':
            return HttpResponseBadRequest()
        comment = Comment.objects.create(path=path.rstrip('/'), body=body, author=request.user)
        if request.is_ajax():
            response = comment.info()
            response['_html'] = render_comment(request, comment)
            return JsonResponse(response)
        else:
            messages.success(request, "Your comment has been added.")
            return HttpResponseRedirect("%s#discourse-comment-%s" % (next, comment.id))
    elif 'delete' in request.GET:
        comment = get_object_or_404(Comment, path=path, id=request.GET['delete'])
        if not request.user == comment.author and not request.user.is_superuser:
            return HttpResponseForbidden()
        comment.delete()
        if request.is_ajax():
            return JsonResponse(True)
        else:
            messages.success(request, "Your comment has been deleted.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def attachments(request, path):
    """
    On delete: delete the file at the path.
    On post: post a new file at the path, unless the 
    On delete with path, delete the file.
    On post with path, replace the file.
    On post without path, create a new file.
    On get with path, download the file.
    On get without path, return a list of files in the thread.
    TODO: On head with path, return info about the file.
    """
    if request.method == 'POST':
        if not request.user.is_superuser:
            return HttpResponse(status=403)
        file = request.FILES['file']
        path = posixpath.join(path, file._name)
        try:
            attachment = Attachment.objects.get(path=path)
        except:
            attachment = Attachment(path=path)
        attachment.file = file
        attachment.mimetype = file.content_type
        attachment.author = request.user
        attachment.save()
        return HttpResponse(json.dumps(attachment.info()), mimetype="application/json")
    elif request.method == 'DELETE' or request.GET.get('method') == 'DELETE':
        if not request.user.is_superuser:
            return HttpResponse(status=403)
        get_object_or_404(Attachment, path=path).delete()
        return HttpResponse(json.dumps(True), mimetype="application/json")
    elif path:
        attachment = get_object_or_404(Attachment, path=path)
        response = HttpResponse(FileWrapper(attachment.file), content_type=attachment.mimetype)
        response['Content-Disposition'] = 'attachment; filename=%s' % attachment.filename
        return response


def document(request, path):
    """
    On head with slot, return info about the content item.
    On delete with slot, delete the content item.
    On post with slot, replace the content item.
    On post without slot, create a new content item.
    On get with slot, download the content item.
    On get without slot, return the contents in the document.

    When changed, update attachments used.
    """
    document = get_object_or_404(Document, path=path.rstrip('/'))
    if request.method == 'POST':
        if not request.user.is_superuser:
            return HttpResponse(status=403)
        attribute = request.POST['attribute']
        body = request.POST['body']
        body = clean_html(body)
        if body.strip() == '':
            document.content.filter(attribute=attribute).delete()
            return HttpResponse(json.dumps(None), mimetype="application/json")
        content, created = document.content.get_or_create(attribute=attribute, defaults={'body': body})
        if not created:
            content.body = body
            content.save()
        return HttpResponse(json.dumps(content.info()), mimetype="application/json")

