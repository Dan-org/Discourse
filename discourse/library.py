from django.db import models
from django.conf import settings

from uri import uri


class Attachment(models.Model):
    anchor_uri = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=255)
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
        return "image/" in self.mimetype

    @property
    def url(self):
        if self.link:
            return self.link
        return "/discourse/attachments/%s" % (self.anchor_uri)

    @property
    def icon(self):
        """
        Returns the icon type for the file.
        """
        if self.link:
            return 'link'
        if "application/pdf" in self.mimetype:
            return "pdf"
        elif "image/" in self.mimetype:
            return "image"
        elif "application/msword" in self.mimetype:
            return "doc"
        elif "officedocument" in self.mimetype:
            return "doc"
        elif self.anchor_uri.endswith(".pages"):
            return "doc"
        return "blank"

    def info(self):
        return {
            'id': self.id,
            'anchor_uri': self.anchor_uri,
            'content_type': self.mimetype,
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

