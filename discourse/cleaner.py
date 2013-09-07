from bleach import clean

ALLOWED_TAGS = """
p blockquote ul ol li br
b strong em i u strike sup sub
img video source a
table td tr th tbody thead caption
""".split()

ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'img': ['src', 'width', 'height', 'alt'],
    'a': ['rel', 'href'],
    'video': ['width', 'height', 'controls'],
    'source': ['src', 'type'],
    'table': ['cellpadding', 'cellspacing'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    'blockquote': ['class']
}


EDITOR_TAGS = """ 
iframe embed
""".split()

EDITOR_ALLOWED_ATTRIBUTES = {
    'iframe': ['src', 'width', 'height', 'frameborder', 'allowfullscreen'],
    'embed': ['src', 'width', 'height', 'allowfullscren', 'wmmode', 'type']
}


def clean_html(src, clean_level=None):
    if (clean_level == 'none'):
        tags = EDITOR_TAGS + ALLOWED_TAGS
        atts = dict(ALLOWED_ATTRIBUTES.items() + EDITOR_ALLOWED_ATTRIBUTES.items())
    else:
        tags = ALLOWED_TAGS
        atts = ALLOWED_ATTRIBUTES        

    return clean(src, tags=tags, attributes=atts, strip=True)

