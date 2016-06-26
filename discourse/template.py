from django.template.loader import render_to_string as django_render_to_string, TemplateDoesNotExist
from django.template import Context, RequestContext

try:
    from jinja2 import Template as JinjaTemplate
    from jinja2 import TemplateNotFound as JinjaTemplateNotFound
except ImportError:
    JinjaTemplate = None
    JinjaTemplateNotFound = None

JINJA = {
    'env': None
}


def set_jinja_env(env):
    JINJA['env'] = env


def render_jinja(template, context, context_update):
    if not JinjaTemplate or not JINJA['env']:
        return None
    
    if not isinstance(template, JinjaTemplate):
        try:
            template = JINJA['env'].get_or_select_template(template)
        except JinjaTemplateNotFound:
            #print "Jinja Doesn't Have:", template
            return None

    if isinstance(context, Context):
        context = context.flatten()

    context = dict(context)
    context.update(context_update)
    return template.render(context)


def render_django(template, context, context_update):
    if not isinstance(context, Context):
        if 'request' in context:
            context = RequestContext(context['request'], context)
        else:
            context = Context(context)

    with context.push(context_update):
        return django_render_to_string(template, context)


def render_to_string(template, context, context_update=None):
    if context.get('JINJA'):
        t = render_jinja(template, context, context_update or {})
        if t is not None:
            return t
    
    return render_django(template, context, context_update or {})
