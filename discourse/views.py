"""

"""
import json, posixpath
from cleaner import clean_html

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden, Http404
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.template import RequestContext

from ajax import JsonResponse
from models import Attachment, Document, Comment
from models import (comment_pre_edit, comment_post_edit, 
                    attachment_pre_edit, attachment_post_edit,
                    document_pre_edit, document_post_edit)
from models import get_instance_from_sig


### Helpers ###
def render_comment(request, comment):
    return render_to_string('discourse/thread-comment.html', locals(), RequestContext(request))

def login_required(fn):
    return user_passes_test(lambda u: u.is_superuser)(fn)


### Views ###
def thread(request, path):
    """
    Comment manipulation
    """
    if request.method == 'POST':
        next = request.POST['next']
        pk = request.POST.get('pk')
        if pk:
            comment = get_object_or_404(Comment, pk=pk, path=path)
            comment.edit_by_request(request)
        else:
            comment = Comment.create_by_request(request, path=path, body=request.POST['body'])

        if request.is_ajax():
            response = comment.info()
            response['_html'] = render_comment(request, comment)
            return JsonResponse(response)
        else:
            return HttpResponseRedirect("%s#discourse-comment-%s" % (next, comment.id))

    elif 'delete' in request.GET:
        comment = get_object_or_404(Comment, pk=request.GET['delete'], path=path)
        comment.delete_by_request(request)
        if request.is_ajax():
            return JsonResponse(True)
        else:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    else:
        return HttpResponseBadRequest()



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
        response['Content-Disposition'] = 'attachment; filename="%s"' % attachment.filename
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


def redirect(request, path):
    """
    Redirects to the object found on the path.
    """
    if (path.startswith('url:')):
        return HttpResponseRedirect(path[4:])
    instance = get_instance_from_sig(path)
    if not instance:
        raise Http404
    return HttpResponseRedirect(instance.get_absolute_url())

