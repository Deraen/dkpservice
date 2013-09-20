# -*- coding: utf-8 -*-
from functools import wraps
from datetime import date, timedelta

from django.core.cache import cache
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect

from dkp.models import *


def raid_period(period):
    return date.today() - timedelta(days=period)


def calculate_percent(dividend, divider):
    """Lasketaan sum ja count prosentit, pyöristys tarkkuus vaikuttaa usable dkp"""
    if divider == 0:
        return 0
    else:
        return round(float(dividend) / divider, 4)


def cache_set(key, value, timeout=None):
    if timeout is None:
        cache.set(key, value)
    else:
        cache.set(key, value, timeout)
    return value


def cached_property(func):
    def cached_func(self):
        key = 'cached_property_%s_%s_%s' % (self.__class__.__name__, func.__name__, self.pk)
        val = cache.get(key)

        if val is None:
            return cache_set(key, func(self))
        return val
    # return wraps(func)(cached_func)
    return property(func)


def cached_method(key, timeout=60):
    def cached_func(func):
        def decorated(self, *args, **kwargs):
            key_params = self.__dict__.copy()
            key_params.update(kwargs)
            formated_key = key.format(**key_params)

            val = cache.get(formated_key)
            if val is None:
                return cache_set(formated_key, func(self, *args, **kwargs), timeout)
            return val
        return decorated
    return cached_func


def render(t):
    def decorator(func):
        def inner_decorator(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            if isinstance(response, HttpResponse) or isinstance(response, HttpResponseRedirect):
                return response
            else:
                return render_to_response(t, response, context_instance=RequestContext(request))
        return wraps(func)(inner_decorator)
    return decorator


def datatables(request, data, sort_columns):
    iDisplayLength = min(int(request.GET.get('iDisplayLength', 10)), 100)
    startRecord = int(request.GET.get('iDisplayStart', 0))
    endRecord = startRecord + iDisplayLength

    iSortingCols = int(request.GET.get('iSortingCols', 0))
    asortingCols = []

    if iSortingCols:
        for sortedColIndex in range(0, iSortingCols):
            sortedColID = int(request.GET.get('iSortCol_' + str(sortedColIndex), 0))
            if request.GET.get('bSortable_{0}'.format(sortedColID), 'false') == 'true':
                sortedColName = request.GET.get('mDataProp_' + str(sortedColID))
                if sortedColName in sort_columns:
                    sortedColName = sort_columns[sortedColName]
                    sortingDirection = request.GET.get('sSortDir_' + str(sortedColIndex), 'asc')
                    if sortingDirection == 'desc':
                        sortedColName = '-' + sortedColName
                    asortingCols.append(sortedColName)

    try:
        data = data.order_by(*asortingCols)
    except:
        pass

    try:
        count = data.count()
    except:
        count = 0

    data = data[startRecord:endRecord]

    return data, count


class QuerySetManager(models.Manager):
    """
    Jotta "manageri" funktioita voi ketjuttaa eli queryseteille samat funktiot.
    """
    def get_query_set(self):
        return self.model.QuerySet(self.model)

    def __getattr__(self, attr, *args):
        try:
            return getattr(self.__class__, attr, *args)
        except AttributeError:
            return getattr(self.get_query_set(), attr, *args)


