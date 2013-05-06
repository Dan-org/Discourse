from django.contrib import admin
from models import DocumentTemplate, Document, DocumentContent, Attachment

### Custom Admins ###
class DocumentContentAdmin(admin.TabularInline):
    model = DocumentContent

class DocumentAdmin(admin.ModelAdmin):
    inlines = [
        DocumentContentAdmin,
    ]

admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentTemplate)
admin.site.register(Attachment)