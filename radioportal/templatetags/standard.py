# -*- encoding: utf-8 -*-
# 
# Copyright © 2012 Robert Weidlich. All Rights Reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# 
# 3. The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE LICENSOR "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.
# 
# -*- coding: utf-8 -*-

from django.conf import settings

from django import template
register = template.Library()

import urlparse

@register.filter
def urlsplit(value, arg):
    result = getattr(urlparse.urlparse(value), arg)
    if arg == "path":
        result = result[1:]
    return result

@register.filter
def startswith(value, arg):
    """Usage, {% if value|starts_with:"arg" %}"""
    if not value:
        return False
    return value.startswith(arg)

@register.filter
def sameday(date1, date2):
    """Usage, {% if date1|sameday:date2 %}"""
    return date1.year == date2.year and date1.month == date2.month and date1.day == date2.day

@register.filter
def contains(value, arg):
    """Usage, {% if value|contains:"arg" %}"""
    return arg in value


@register.filter
def hashEpisode(episode, what):
    if what == "content":
        val = episode.description
        val += episode.title
        val += episode.currentSong
        val += episode.genre
        return hash()
    if what == "streams":
        if episode.channel:
            val = episode.channel.stream_set.values_list('id', 'running')
            return hash(val)
        else:
            return 0


@register.filter
def object_name(value):
    return value._meta.object_name


@register.filter
def formataudio(number, format):
    """Usage: {{ stream.bitrate|formataudio:stream.format }}"""
    if format == "mp3":
        if number[-1] == 'k':
            number = number[:-1]
        return "%sKBit/s" % (number,)
    elif format == "ogg":
        if "q" in number:
            return "Quality %s" % (number[1:],)
        else:
            if number[-1] == 'k':
                number = number[:-1]
            return "%sKBit/s" % (number,)
    else:
        return number

from django.template import Node
from django.utils.encoding import smart_str


# copied from django.template.defaulttags to support custom urlconf
class URLNode(Node):
    def __init__(self, view_name, args, kwargs, asvar, legacy_view_name=True):
        self.view_name = view_name
        self.legacy_view_name = legacy_view_name
        self.args = args
        self.kwargs = kwargs
        self.asvar = asvar

    def render(self, context):
        from django.core.urlresolvers import reverse, NoReverseMatch
        args = [arg.resolve(context) for arg in self.args]
        urlconf = None
        if "urlconf" in self.kwargs:
            urlconf = str(self.kwargs["urlconf"])
            del self.kwargs["urlconf"]
        kwargs = dict([(smart_str(k, 'ascii'), v.resolve(context))
                       for k, v in self.kwargs.items()])

        view_name = self.view_name
        if not self.legacy_view_name:
            view_name = view_name.resolve(context)

        # Try to look up the URL twice: once given the view name, and again
        # relative to what we guess is the "main" app. If they both fail,
        # re-raise the NoReverseMatch unless we're using the
        # {% url ... as var %} construct in which cause return nothing.
        url = ''
        try:
            url = reverse(view_name, urlconf=urlconf, args=args,
                          kwargs=kwargs, current_app=context.current_app)
        except NoReverseMatch, e:
            if settings.SETTINGS_MODULE:
                project_name = settings.SETTINGS_MODULE.split('.')[0]
                try:
                    url = reverse(project_name + '.' + view_name,
                              args=args, kwargs=kwargs,
                              current_app=context.current_app)
                except NoReverseMatch:
                    if self.asvar is None:
                        # Re-raise the original exception, not the one with
                        # the path relative to the project. This makes a
                        # better error message.
                        raise e
            else:
                if self.asvar is None:
                    raise e

        if self.asvar:
            context[self.asvar] = url
            return ''
        else:
            return url

from django.template import defaulttags
defaulttags.URLNode = URLNode

import time, hashlib

from django.utils.http import urlquote

@register.filter
def secdownload(rel_path):
    secret = getattr(settings, "RP_DL_SECRET", "verysecret")
    uri_prefix = getattr(settings, "RP_DL_PREFIX", "/dl/")
    hextime = "%08x" % time.time()
    token = hashlib.md5((secret + rel_path + hextime).encode('utf-8')).hexdigest()
    return '%s%s/%s%s' % (uri_prefix, token, hextime, urlquote(rel_path))

import os.path

@register.filter
def fileexists(rel_path):
    if rel_path[0] == "/":
        rel_path = rel_path[1:]
    base = getattr(settings, 'RP_DL_BASEDIR', '/tmp/')
    path = os.path.join(base, rel_path)
    return os.path.exists(path)
