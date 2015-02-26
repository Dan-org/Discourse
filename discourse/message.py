from django.db import models
from django.conf import settings
from uuidfield import UUIDField



class Channel(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    tags = models.TextField(blank=True)
    keys = models.TextField(blank=True)
    publish_keys = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related="channels")


class Message(models.Model):
    uuid = UUIDField(auto=True)
    type = models.SlugField(max_length=255)
    channel = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=0)
    parent = models.ForeignKey("Message", blank=True, null=True, related="children")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related="messages")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    tags = models.TextField(blank=True)
    keys = models.TextField(blank=True)
    content = models.TextField(blank=True)

    def __unicode__(self):
        return "Message(%r, %r, %r)" % (self.uuid, self.type, self.channel)


class Attachment(models.Model):
    uuid = UUIDField(auto=True)
    message = models.ForeignKey(Message)
    mimetype = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    source = models.FileField()


with discourse(request, "site"):
    project = Circle.objects.create(name="Hi", type="project")

    -> m = Message(type="operations.create", channel="site", content={'name': 'Hi', 'type': 'Project'})
    -> project = m.play()


::operations.py
    def create(message):    
        message.cancel()




class Flag(models.Model):
    uuid = UUID("The UUID of the mark.")
    channel = String("Context of where it happens.")
    type = Stirng("Type of mark")
    user = models.ForeignKey(settings.AUTH_USER_MODEL)



class Attachment(models.Model):
    uuid = UUID("The UUID of the message.")
    mimetype = ...
    source = ...
    name = ...
    version = ...


class Message(Interface):
    uuid = UUID("The UUID of the message.")
    type = String("The type of message this is.")
    channel = String("The context of the message/where it happens")
    parent = UUID("A parent message.", required=False)
    sender = String("The sender")
    tags = List("A list of tags", type=String, required=False)
    require = List("A list of keys, a user shouldn't have access unless they has one of the keys present.", type=String, required=False)
    content = Anything("Content of the message.", required=False)
    attachments = List("A list of attachments", type=Attachment, required=False)
    created = ...


def index_message(message):
    """
    Take a message, and then return an indexable object that represents its current state.
    """
    pass


def view_document(document_url):
    document = search(Document)



def thread(object)


class StateCollection(set):
    pass


class StateModel(dict):
    def __getattr__(self, k):
        return self.__getitem__(self, k)

    def save(self):
        pass

    def delete(self):
        pass




class Message(object):
    pass



def publish():
    """
    Creates a new message, publishes it.
    """
    pass

def apply(messages):
    """
    Returns a list of end states based on the messages.
    """
    pass

def hook():
    """
    Binds a function to be run when a sort of message is published.
    """
    pass

def history(messages):
    """
    Returns a list of versioned states based on the messages.
    """
    pass

def search():
    """
    Returns a result-set of messages that satisfy the search criteria
    """
    pass

def expire(message, time):
    """
    Sets the message to expire after time.
    """

def save(message):
    """
    Sets the message to never expire, identical to ``expire(message, None)``
    """
    return expire(message, time=None)

def patch(id, message, safe=True):
    """
    Updates the message with the given id.  By default, this will ensure the write was not preempted by
    another write.  Set ``safe`` to ``False`` to ignore this.
    """
    pass

def put(message):
    """
    Adds a new message to the system without publishing it.
    """
    pass


"""
message message message -> scalar

messages = set([])
apply(messages) -> object


message = {
    _id: '29c88235d3674cf68be097aae58989b2',
    _type: 'status:post',
    _delta': '679afa7971cb13874cf8b278a7050291',
    _actor: 'user:525',
    _published: '1415507180.157795',
    _tags: [],
    target: 'project:23',
    body: '...',
    audience: 'project'
}

message = {
    _id: 'b1387677971c4cf9afa8a7050291b278',
    _context: '29c88235d3674cf68be097aae58989b2',
    _type: 'create'
    _published: '1415507180.157849'
}

message = {
    _id: 'b1387677971c4cf9afa8a7050291b278',
    _context: '29c88235d3674cf68be097aae58989b2',
    _type: 'forbidden'
    _published: '1415507180.157849'
}

apply(messages) -> 




> watch('comment', ...)
DEBUG - Message sent "comment"
DEBUG - Message caught by "audit" - app.py:30
DEBUG - Message phase set to "audited"
DEBUG - Message caught by "save_comment" - app.py:42
DEBUG - Message phase set to "commited"
DEBUG - Message("comment", 9aa3b2) archived


DEBUG - Message("thing", 457f2a) expiry set for 18:30.305 today


DEBUG - Message("job", 5f2a5b) sent
DEBUG - Message("job", 5f2a5b) caught by "scheduler" - tasks.py:354


DEBUG - Message("job", 5f2a5b) caught and owned by process:14455 - python worker.py


def clean(messages):
    pass


message = {
    _id: 'b1387677971c4cf9afa8a7050291b278',
    _context: '29c88235d3674cf68be097aae58989b2',
    _type: 'edit'
    _published: '1415507180.157849'
}

messages = [...]

state_history(messages) -> [state, state, state, state]
"""