"""

"""
import json, posixpath, mimetypes
from cleaner import clean_html

from django.utils.text import slugify
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden, Http404
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.template import RequestContext
from django.conf import settings

from ajax import JsonResponse
from models import Attachment, AttachmentZip, Document, Comment, CommentVote, Event
from models import attachment_manipulate, comment_manipulate, document_manipulate, attachment_view, comment_vote
from models import get_instance_from_sig

from notice import subscribe, unsubscribe

try:
    import redis
    redis = redis.Redis(host='localhost', port=6379, db=getattr(settings, 'REDIS_DB', 1))
except ImportError:
    redis = None


### Helpers ###
def publish(path, **args):
    if redis:
        redis.publish(path, json.dumps(args))


def render_comment(request, comment, scored=False):
    return render_to_string('discourse/thread-comment.html', locals(), RequestContext(request))


def get_files(request):
    ids = request.POST.getlist('ids', request.POST.getlist('ids[]', None))
    return Attachment.objects.filter(id__in=ids)


### Views ###
def thread(request, path):
    """
    Comment manipulation
    """
    if request.method == 'POST':
        next = request.POST.get('next', None)
        pk = request.POST.get('pk')
        if pk:
            comment = get_object_or_404(Comment, pk=pk, path=path)
            comment.edit_by_request(request, body=request.POST['body'])
        else:
            comment = Comment.create_by_request(request, path=path, body=request.POST['body'])

        data = comment.info()
        data['_html'] = render_comment(request, comment, scored=request.POST.get('scored', '').lower() == 'true')

        publish(comment, type='comment', comment=data)

        if request.is_ajax():
            return JsonResponse(data)
        else:
            return HttpResponseRedirect("%s#discourse-comment-%s" % (next, comment.id))

    elif 'delete' in request.GET:
        comment = get_object_or_404(Comment, pk=request.GET['delete'], path=path)

        publish(comment, type='delete', id=comment.id)

        comment.delete_by_request(request)

        if request.is_ajax():
            return JsonResponse(True)
        else:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    else:
        return HttpResponseBadRequest()


def vote(request):
    if request.method == 'POST' and request.user.is_authenticated():
        direction = request.POST['dir']
        comment = get_object_or_404(Comment, pk=request.POST['pk'])
        try:
            vote = comment.votes.get(user=request.user)
        except CommentVote.DoesNotExist:
            vote = CommentVote(user=request.user, comment=comment)
        if direction == '-1':
            vote.value = -1
        elif direction == '1':
            vote.value = 1
        else:
            vote.value = 0
        for reciever, response in comment_vote.send(sender=comment, request=request, vote=vote):
            if isinstance(response, HttpResponse):
                return response
        if (vote.value == 0):
            if vote.id is not None:
                vote.delete()
            else:
                return JsonResponse(comment.value)
        else:
            vote.save()

        comment.save()
        publish(comment.path, type='vote', id=comment.id, value=comment.value)
        return JsonResponse(comment.value)
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
    if request.method == 'DELETE' or request.POST.get('method') == 'delete':
        for attachment in get_files(request):
            for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='delete'):
                if isinstance(response, HttpResponse):
                    return response
            attachment.delete()
        return HttpResponse(json.dumps(True), content_type="application/json")
    elif request.POST.get('method') == 'hide':
        for attachment in get_files(request):
            for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='hide'):
                if isinstance(response, HttpResponse):
                    return response
            attachment.hidden = True
            attachment.save()
        return HttpResponse(json.dumps(True), content_type="application/json")
    elif request.POST.get('method') == 'show':
        for attachment in get_files(request):
            for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='show'):
                if isinstance(response, HttpResponse):
                    return response
            attachment.hidden = False
            attachment.save()
        return HttpResponse(json.dumps(True), content_type="application/json")
    elif request.POST.get('method') == 'zip':
        attachments = []
        for attachment in get_files(request):
            for reciever, response in attachment_view.send(sender=attachment, request=request):
                if isinstance(response, HttpResponse):
                    return response
            attachments.append(attachment)
        zip = AttachmentZip.create(attachments)
        response = HttpResponse(json.dumps(zip.info()), content_type="application/json", status=202)
        response['Location'] = zip.url
        return response
    elif request.POST.get('method') == 'rename':
        attachment = get_files(request)[0]
        for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='rename'):
            if isinstance(response, HttpResponse):
                return response
        attachment.filename = request.POST['filename']
        attachment.save()
        return HttpResponse(json.dumps(attachment.info()), content_type="application/json")
    elif request.method == 'POST' and request.POST.get('link'):
        url = request.POST['link']
        if '://' not in url:
            url = 'http://' + url
        filename = url
        if '?' in filename:
            filename = filename.split('?', 1)[0]
        if '/' in filename:
            filename = url.rsplit('/', 1)[1]
        if '.' not in filename:
            filename = slugify(filename)
        path = posixpath.join(path, filename)
        try:
            attachment = Attachment.objects.get(path=path)
        except:
            attachment = Attachment(path=path, link=url)
        attachment.file = None
        attachment.mimetype, encoding = mimetypes.guess_type(filename)
        if attachment.mimetype is None:
            attachment.mimetype = '?'
        attachment.author = request.user
        for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='create'):
            if isinstance(response, HttpResponse):
                return response
        attachment.save()
        return HttpResponse(json.dumps(attachment.info()), content_type="application/json")
    elif request.method == 'POST':
        file = request.FILES['file']
        path = posixpath.join(path, file._name)
        try:
            attachment = Attachment.objects.get(path=path)
        except:
            attachment = Attachment(path=path)
        attachment.file = file
        attachment.mimetype = file.content_type
        attachment.author = request.user
        for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='create'):
            if isinstance(response, HttpResponse):
                return response
        attachment.save()
        return HttpResponse(json.dumps(attachment.info()), content_type="application/json")
    elif path:
        attachment = get_object_or_404(Attachment, path=path)
        for reciever, response in attachment_view.send(sender=attachment, request=request):
            if isinstance(response, HttpResponse):
                return response
        if not attachment.file.storage.exists(attachment.file.path):
            raise Http404
        response = HttpResponse(FileWrapper(attachment.file), content_type=attachment.mimetype)
        response['Content-Length'] = attachment.file.storage.size(attachment.file.path)
        response['Content-Disposition'] = "filename=%s" % attachment.file.name
        return response


def zip(request, hash):
    """
    Downloads the zip with the given hash.
    """
    zip = get_object_or_404(AttachmentZip, hash=hash)
    if 'poll' in request.GET:
        response = HttpResponse(json.dumps(zip.info()), content_type='application/json')
    elif zip.status == 'failed':
        response = HttpResponse("Attachment compression failed.", status=500)
    elif zip.status == 'working':
        response = HttpResponse("Attachment compression working.", status=202)
        response['Location'] = zip.url
    else:
        response = HttpResponse(FileWrapper(zip.file), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="Attachments.zip"'
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
    try:
        if request.method == 'POST':
            attribute = request.POST['attribute']
            value = request.POST['value']
            for reciever, response in document_manipulate.send(sender=document, request=request, action='edit'):
                if isinstance(response, HttpResponse):
                    return response
            value = clean_html(value)
            if value.strip() == '':
                document.content.filter(attribute=attribute).delete()
                return HttpResponse(json.dumps(None), content_type="application/json")
            content, created = document.content.get_or_create(attribute=attribute, defaults={'body': value})
            if not created:
                content.body = value
                content.save()
            return HttpResponse(json.dumps(content.info(locals())), content_type="application/json")
    except Exception, e:
        print e
        raise


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


def property(request, path):
    """
    Updates the property on an object given the path.
    """
    property = request.POST['property']
    value = request.POST['value']
    instance = get_instance_from_sig(path)
    if not instance:
        raise Http404
    setattr(instance, property, value)
    instance.save()
    return HttpResponse(json.dumps( getattr(instance, property, value) ), content_type="application/json")


@login_required
def subscriber(request):
    if not request.method == 'POST':
        return HttpResponseBadRequest()

    path = request.POST.get('path')
    toggle = request.POST.get('toggle', 'true').lower() in ('true', 'on', 'yes')
    if toggle:
        subscribe(request.user, path, force=True)
    else:
        unsubscribe(request.user, path)

    return HttpResponse(toggle, content_type="application/json")


@login_required
def monitor(request):
    """
    Monitor all events happening on the system.
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    events = Event.objects.all()[:50]
    return render(request, 'discourse/monitor.html', locals())


def test(request):
    if not settings.DEBUG:
        raise Http404
    return render(request, 'discourse/test.html', locals())
