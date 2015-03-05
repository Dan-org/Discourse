import json, mimetypes, urllib, urllib2, re

from django.db import models
from django.conf import settings
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest, HttpResponseRedirect

from uri import *
from event import publish
from ajax import JsonResponse


class Attachment(models.Model):
    anchor_uri = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    caption = models.TextField(blank=True)
    featured = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True, blank=True, null=True)
    order = models.IntegerField(default=0)
    file = models.FileField(upload_to="attachments", blank=True, null=True)
    link = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ('anchor_uri', 'filename')

    def __unicode__(self):
        return self.anchor_uri

    def __repr__(self):
        return "Attachment(%r)" % (self.anchor_uri)

    def is_an_image(self):
        return "image/" in self.content_type

    @property
    def url(self):
        return reverse("discourse:library", args=(self.anchor_uri,)) + "/" + urllib.quote( self.filename )

    @property
    def icon(self):
        """
        Returns the icon type for the file.
        """
        if self.link:
            return 'link'
        if "application/pdf" in self.content_type:
            return "pdf"
        elif "image/" in self.content_type:
            return "image"
        elif "application/msword" in self.content_type:
            return "doc"
        elif "officedocument" in self.content_type:
            return "doc"
        elif self.anchor_uri.endswith(".pages"):
            return "doc"
        return "blank"

    def info(self):
        return {
            'id': self.id,
            'anchor_uri': self.anchor_uri,
            'content_type': self.content_type,
            'caption': self.caption,
            'order': self.order,
            'filename': self.filename,
            'url': self.url,
            'icon': self.icon,
            'hidden': self.hidden,
            'link': self.link
        }

    #@classmethod
    #def get_folder(cls, path):
    #    """
    #    Returns a QuerySet of the media in the given ``path`` folder.
    #    """
    #    if not path.endswith('/'):
    #        path = path + '/'
    #    return cls._default_manager.filter(filename__startswith=path)

    class Meta:
        app_label = 'discourse'


### Template Tags ###
import ttag

class LibraryTag(ttag.Tag):
    """
    Creates a media library for the given object or current page.
    """
    anchor = ttag.Arg(required=False)                                   # Object or string to anchor to.
    sub = ttag.Arg(default=None, keyword=True, required=False)          # The sub-anchor

    class Meta:
        name = "library"

    def render(self, context):
        data = self.resolve(context)
        request = context['request']
        anchor = uri(data.get('anchor'), data.get('sub'))
        attachments = Attachment.objects.filter(anchor_uri=anchor)
        context['library'] = anchor

        context_vars = {'attachments': attachments,
                        'anchor': anchor,
                        'is_empty': False,
                        'request': request}

        try:
            e = publish(anchor, request.user, 'view-library', data={'editable': request.user.is_superuser}, internal=True)
            if not e:
                return ""
        except PermissionDenied:
            return ""

        context_vars['json'] = json.dumps([a.info() for a in attachments])
        context_vars['editable'] = e.data['editable']

        return render_to_string('discourse/library.html', context_vars, context)


### Views ###
def get_attachment_changes(request):
    changes = {}

    if 'hidden' in request.POST:
        hidden = request.POST['hidden'].lower()
        if hidden in ('yes', 'true'):
            changes['hidden'] = True
        else:
            changes['hidden'] = False

    if 'filename' in request.POST:
        changes['filename'] = request.POST['filename']

    if 'featured' in request.POST:
        changes['featured'] = request.POST['featured']

    if 'caption' in request.POST:
        changes['caption'] = request.POST['caption']

    if 'content_type' in request.POST:
        changes['content_type'] = request.POST['content_type']

    if 'order' in request.POST:
        try:
            changes['order'] = int( request.POST['order'] )
        except ValueError:
            return HttpResponseBadRequest()

    return changes

def upload(request, anchor, filename):
    anchor = uri(anchor)

    if 'link' in request.POST:
        link = request.POST['link']
        if '://' not in link:
            link = 'http://' + link
        filename = find_filename_for_url( link )
        attachment = Attachment(anchor_uri=anchor, filename=filename, link=link)
        content_type = 'text/url'
    else:
        filename = filename or request.FILES['attachment'].name

        try:
            attachment = Attachment.objects.get(anchor_uri=anchor, filename=filename)
        except:
            attachment = Attachment(anchor_uri=anchor, filename=filename)

        attachment.file = request.FILES['attachment']
        content_type = request.POST.get('content_type', getattr(attachment.file, 'content_type', mimetypes.guess_type(filename or attachment.file.name)[0]))

    properties = {'filename': filename, 'content_type': content_type}
    properties.update( get_attachment_changes(request) )

    if not publish(anchor, request.user, 'attach', data=properties, record=True):
        raise PermissionDenied()

    for k, v in properties.items():
        setattr(attachment, k, v)

    attachment.author = request.user
    attachment.save()
    return JsonResponse(attachment.info())


def find_filename_for_url(url):
    try:
        text = urllib2.urlopen(url, timeout=10).read()
    except:
        pass
    else:
        match = re.search(r"\<\s*title\s*\>(.*?)\<\s*\/title\s*>", text, re.I | re.M)
        if match:
            return match.groups()[0].strip()

    filename = url
    if '?' in filename:
        filename = filename.split('?', 1)[0]
    if '/' in filename:
        filename = url.rsplit('/', 1)[1]
    if '.' not in filename:
        filename = slugify(filename)

    return filename


def edit_attachment(request, anchor, filename):
    anchor = uri(anchor)

    attachment = get_object_or_404(Attachment, anchor_uri=anchor, filename=filename)

    properties = get_attachment_changes(request)

    if not properties:
        return HttpResponseBadRequest()

    if not publish(attachment, request.user, 'edit', data=properties, record=True):
        raise PermissionDenied()

    for k, v in properties.items():
        setattr(attachment, k, v)

    attachment.save()
    return JsonResponse(attachment.info())


def delete_attachment(request, anchor, filename):
    anchor = uri(anchor)
    attachment = get_object_or_404(Attachment, anchor_uri=anchor, filename=filename)

    if not publish(attachment, request.user, 'delete', record=True):
        raise PermissionDenied()

    data = attachment.info()
    attachment.delete()
    data['deleted'] = True
    return JsonResponse(data)


def download_attachment(request, anchor, filename):
    anchor = uri(anchor)
    attachment = get_object_or_404(Attachment, anchor_uri=anchor, filename__iexact=filename)

    if not publish(attachment, request.user, 'download', record=False):
        raise PermissionDenied()

    if attachment.content_type == 'text/url':
        return HttpResponseRedirect(attachment.link)

    return HttpResponseRedirect(attachment.file.url)


def manipulate(request, uri):
    """
    Manipulate the attachments.
    """
    anchor, filename = resolve_model_uri(uri)

    if filename:
        filename = urllib.unquote(filename)
    elif 'filename' in request.POST:
        filename = request.POST['filename']
    elif 'filename' in request.GET:
        filename = request.GET['filename']

    if request.method == 'DELETE' or request.POST.get('delete', '').lower() in ('yes', 'true'):
        return delete_attachment(request, anchor, filename)
    elif 'attachment' in request.FILES or 'link' in request.POST:
        return upload(request, anchor, filename)
    elif request.POST:
        return edit_attachment(request, anchor, filename)
    else:
        return download_attachment(request, anchor, filename)


#    """
#    On delete: delete the file at the path.
#    On post: post a new file at the path, unless the 
#    On delete with path, delete the file.
#    On post with path, replace the file.
#    On post without path, create a new file.
#    On get with path, download the file.
#    On get without path, return a list of files in the thread.
#    TODO: On head with path, return info about the file.
#    """
#    anchor, filename = resolve_model_uri(uri)
#
#    if request.method == 'DELETE' or request.POST.get('delete', '').lower() in ('yes', 'true'):
#        return delete_attachment(request, anchor, filename)
#    elif 'file' in request.FILES:
#        return upload(request, anchor, filename)
#    elif request.POST:
#        return edit_attachment(request, anchor, filename)
#    else:
#        return download_attachment(request, anchor, filename)
#
#
#    if request.method == 'DELETE' or request.POST.get('method') == 'delete':
#        for attachment in get_files(request):
#            for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='delete'):
#                if isinstance(response, HttpResponse):
#                    return response
#            attachment.delete()
#        return HttpResponse(json.dumps(True), content_type="application/json")
#    elif request.POST.get('method') == 'hide':
#        for attachment in get_files(request):
#            for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='hide'):
#                if isinstance(response, HttpResponse):
#                    return response
#            attachment.hidden = True
#            attachment.save()
#        return HttpResponse(json.dumps(True), content_type="application/json")
#    elif request.POST.get('method') == 'show':
#        for attachment in get_files(request):
#            for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='show'):
#                if isinstance(response, HttpResponse):
#                    return response
#            attachment.hidden = False
#            attachment.save()
#        return HttpResponse(json.dumps(True), content_type="application/json")
#    elif request.POST.get('method') == 'zip':
#        attachments = []
#        for attachment in get_files(request):
#            for reciever, response in attachment_view.send(sender=attachment, request=request):
#                if isinstance(response, HttpResponse):
#                    return response
#            attachments.append(attachment)
#        zip = AttachmentZip.create(attachments)
#        response = HttpResponse(json.dumps(zip.info()), content_type="application/json", status=202)
#        response['Location'] = zip.url
#        return response
#    elif request.POST.get('method') == 'rename':
#        attachment = get_files(request)[0]
#        for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='rename'):
#            if isinstance(response, HttpResponse):
#                return response
#        attachment.filename = request.POST['filename']
#        attachment.save()
#        return HttpResponse(json.dumps(attachment.info()), content_type="application/json")
#    elif request.method == 'POST' and request.POST.get('link'):
#        url = request.POST['link']
#        if '://' not in url:
#            url = 'http://' + url
#        filename = url
#        if '?' in filename:
#            filename = filename.split('?', 1)[0]
#        if '/' in filename:
#            filename = url.rsplit('/', 1)[1]
#        if '.' not in filename:
#            filename = slugify(filename)
#        path = posixpath.join(path, filename)
#        try:
#            attachment = Attachment.objects.get(path=path)
#        except:
#            attachment = Attachment(path=path, link=url)
#        attachment.file = None
#        attachment.mimetype, encoding = mimetypes.guess_type(filename)
#        if attachment.mimetype is None:
#            attachment.mimetype = '?'
#        attachment.author = request.user
#        for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='create'):
#            if isinstance(response, HttpResponse):
#                return response
#        attachment.save()
#        return HttpResponse(json.dumps(attachment.info()), content_type="application/json")
#    elif request.method == 'POST':
#        file = request.FILES['file']
#        path = posixpath.join(path, file._name)
#        try:
#            attachment = Attachment.objects.get(path=path)
#        except:
#            attachment = Attachment(path=path)
#        attachment.file = file
#        attachment.mimetype = file.content_type
#        attachment.author = request.user
#        for reciever, response in attachment_manipulate.send(sender=attachment, request=request, action='create'):
#            if isinstance(response, HttpResponse):
#                return response
#        attachment.save()
#        return HttpResponse(json.dumps(attachment.info()), content_type="application/json")
#    elif path:
#        attachment = get_object_or_404(Attachment, path=path)
#        for reciever, response in attachment_view.send(sender=attachment, request=request):
#            if isinstance(response, HttpResponse):
#                return response
#        if not attachment.file.storage.exists(attachment.file.name):
#            raise Http404
#        response = HttpResponse(FileWrapper(attachment.file), content_type=attachment.mimetype)
#        response['Content-Length'] = attachment.file.storage.size(attachment.file.name)
#        response['Content-Disposition'] = "filename=%s" % attachment.file.name
#        return response
#