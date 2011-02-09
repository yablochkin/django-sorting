from django import template
from django.conf import settings
from django.template import TemplateSyntaxError
from django.utils.translation import ugettext as _
from django.core.exceptions import FieldError

register = template.Library()

DEFAULT_SORT_UP = getattr(settings, 'DEFAULT_SORT_UP' , '&uarr;')
DEFAULT_SORT_DOWN = getattr(settings, 'DEFAULT_SORT_DOWN' , '&darr;')

SORTING_NOFOLLOW = getattr(settings, 'SORTING_NOFOLLOW', True)

sort_directions = {
    'asc': {'icon':DEFAULT_SORT_UP, 'inverse': 'desc'},
    'desc': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'},
    '': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'},
}

def anchor(parser, token):
    """
    Parses a tag that's supposed to be in this format: {% anchor field title %}
    Title may be a "string", _("trans string"), or variable
    """
    bits = [b for b in token.split_contents()]
    if len(bits) < 2:
        raise template.TemplateSyntaxError, "anchor tag takes at least 1 argument"

    try:
        title = bits[2]
        if title[0] in ('"', "'"):
            if title[0] == title[-1]:
                title = title[1:-1]
            else:
                raise TemplateSyntaxError, 'anchor tag title must be a "string", _("trans string"), or variable'
        elif title.startswith('_("') or title.startswith("_('"):
            title = _(title[3:-2])

    except IndexError:
        title = bits[1].capitalize()
    return SortAnchorNode(bits[1].strip(), title.strip())
    

class SortAnchorNode(template.Node):
    """
    Renders an <a> HTML tag with a link which href attribute 
    includes the field on which we sort and the direction.
    and adds an up or down arrow if the field is the one 
    currently being sorted on.

    Eg.
        {% anchor name Name %} generates
        <a href="/the/current/path/?sort=name" title="Name">Name</a>

    """
    def __init__(self, field, title):
        self.field = field
        self.title = title

    def render(self, context):
        try:
            self.title = template.Variable(self.title).resolve(context)
        except (template.VariableDoesNotExist, UnicodeEncodeError):
            pass
            
        request = context['request']
        getvars = request.GET.copy()
        if 'sort' in getvars:
            sortby = getvars['sort']
            del getvars['sort']
        else:
            sortby = ''
        if 'dir' in getvars:
            sortdir = getvars['dir']
            del getvars['dir']
        else:
            sortdir = ''
        if sortby == self.field:
            getvars['dir'] = sort_directions[sortdir]['inverse']
            icon = sort_directions[sortdir]['icon']
        else:
            icon = ''
        if len(getvars.keys()) > 0:
            urlappend = "&%s" % getvars.urlencode()
        else:
            urlappend = ''
        if icon:
            title = "%s %s" % (self.title, icon)
        else:
            title = self.title

        url = '%s?sort=%s%s' % (request.path, self.field, urlappend)
        if SORTING_NOFOLLOW:
            return '<a href="%s" title="%s" rel="nofollow">%s</a>' % (url, self.title, title)
        else:
            return '<a href="%s" title="%s">%s</a>' % (url, self.title, title)


def autosort(parser, token):
    bits = [b.strip('"\'') for b in token.split_contents()]
    help_msg = u'autosort tag synopsis: {%% autosort queryset [as '\
        u'context_variable] %%}'
    context_var = None

    # Check if has not required "as new_context_var" part
    if len(bits) == 4 and bits[2] == 'as':
        context_var = bits[3]
        del bits[2:]
    
    if len(bits) != 2:
        raise template.TemplateSyntaxError(help_msg)

    queryset = bits[1]
    return SortedDataNode(bits[1], context_var=context_var)

class SortedDataNode(template.Node):
    """
    Automatically sort a queryset with {% autosort queryset %}
    """
    def __init__(self, queryset_var, context_var=None):
        self.queryset_var = template.Variable(queryset_var)
        self.context_var = context_var

    def render(self, context):
        if self.context_var is not None:
            key = self.context_var
        else:
            key = self.queryset_var.var
        value = self.queryset_var.resolve(context)
        order_by = context['request'].field
        if len(order_by) > 1:
            try:
                context[key] = value.order_by(order_by)
            except (template.TemplateSyntaxError, FieldError), e:
                context[key] = value
        else:
            context[key] = value

        return ''

anchor = register.tag(anchor)
autosort = register.tag(autosort)

