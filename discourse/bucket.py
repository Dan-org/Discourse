

class BucketModel(models.Model):
    """
    A library model devides each object into a bucket called a "Library".

    If given 
    """
    library_name = models.CharField(max_length=255)

    class Meta:
        abstract = True

    @classmethod
    def get_library(cls, lib):
        """
        Returns a tuple of ``(lib, objects)`` where ``lib`` is the library name and ``objects`` are the objects with that library.

        ``lib`` can be passed in as a model instance in which case it is translated to ``"model-pk"`` where model is the 
        instance model name, lower case and 
        """
        if isinstance(lib, models.Model):
            lib = "%s-%s" % (lib.__class__.__name__.lower(), lib._get_pk_val())
        return lib, cls._default_manager.filter(library_name=lib)


