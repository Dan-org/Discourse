Overview
====================

Discourse is a general Django app currently in the early stages of development for content and communication.  
It acts as the filler of the website, without defining the basic functionality.

It adds the following capabilities:

- Comment System
- Content Editing and Organization (wiki like content editing of structured content)
- Media Library (media uploads as attachment's to objects)
- Calendar System (gleens support)
- Event Stream System (like a facebook or twitter feed)



Thoughts
======================
publish('comment.create', {
    'path': 'loft/report/24/prompt/5/',
    'url': '/discourse/{{asdf}}/',
    't': 1235134523.42,
    'comment': {
        'id': comment.id,
        'raw': comment.body,
        'body': comment.render_body(),
    },
    'actor': {
        'id': comment.
        'name': 'Bill',
        'thumbnail': '/static/{{asdf}}'
    }
})