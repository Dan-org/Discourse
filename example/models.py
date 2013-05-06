from django.db import models

class Page(models.Model):
    path = models.CharField(max_length=255)
    title = models.CharField(max_length=255)

    #attachments = discourse.Library()
    #comments = discourse.Thread()
    #content = discourse.Document()

    #thingers = models.ManyToManyField("Thinger")

    def __unicode__(self):
        return self.path
