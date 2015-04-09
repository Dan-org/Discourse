from django.contrib import admin

from models import (
    DocumentTemplate, Document, DocumentContent
)

class DocumentContentAdmin(admin.TabularInline):
    model = DocumentContent

class DocumentAdmin(admin.ModelAdmin):
    inlines = [
        DocumentContentAdmin,
    ]

admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentTemplate)


#from models import (
#    DocumentTemplate, Document, DocumentContent, 
#    Attachment, 
#    Comment, 
#    Record, 
#    Subscription,
#    Favorite
#)
#
#
#### Custom Admins ###
#class DocumentContentAdmin(admin.TabularInline):
#    model = DocumentContent
#
#class DocumentAdmin(admin.ModelAdmin):
#    inlines = [
#        DocumentContentAdmin,
#    ]
#
#admin.site.register(Document, DocumentAdmin)
#admin.site.register(DocumentTemplate)
#admin.site.register(Attachment)
#admin.site.register(Comment)
#admin.site.register(Record)
#admin.site.register(Subscription)
#admin.site.register(Favorite)