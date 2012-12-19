#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cStringIO as StringIO

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse

from bob import csvutil


class DataTableColumn(object):
    """
    A container object for all the information about a columns header

    :param choice - set if field is dj.choices object
    :param header_name - name to display in columns header
    :param field - field name in model
    :param type - icon type generated by bob header_table tag
    :param selectable - header in bob tag is selectable
    :param bob_tag - set if the column is to be generated by bob tag
    """
    def __init__(self, header_name, choice=None, field=None, type=None,
                 selectable=None, bob_tag=None):
        self.header_name = header_name
        self.choice = choice
        self.field = field
        self.type = type
        self.selectable = selectable
        self.bob_tag = bob_tag


class DataTableMixin(object):
    """Add this Mixin to your django view to handle page pagination.

    In your controller:
    1. Inherit from this mixin
    2. Define ROW_PER_SIZE attribute
    3. Define FILE_NAME attribute
    4. Define columns attribute containing a list of
    :py:class:bob.data_table.DataTableColumn objects
    5. In get() function call self.paginate_query(your_query, columns).

    Result is stored in the
    :py:attr:bob.data_table.DataTableMixin.page_contents
    Data for template can be obtained from
    :py:method:bob.data_table.DataTableMixin.get_context_data_paginator()
    dict to the template.

    In your template add code::

    {% pagination page url_query=url_query show_all=0 show_csv=0 fugue_icons=1 sort_variable_name %}

    where ``query_variable_name`` - is the name of the attribute used for pagination, and::

    {% table_header columns url_query sort fugue_icons%}

    All done!

    """

    csv_file_name = 'file.csv'
    query_variable_name = 'page'
    rows_per_page = 15
    sort = None

    def get_csv_header(self):
        """Generate a list of columns used in csv file header"""
        return [col.header_name for col in self.columns if col.export]

    def get_choice_name(self, obj, field):
        """Generate name value if  an object is a field uses choices"""
        if obj:
            try:
                return getattr(obj, 'get_' + field + '_display')()
            except AttributeError:
                pass
        return ''

    def get_export_response(self, **kwargs):
        """Should be used if you want to return export file"""
        return self.response

    def get_context_data_paginator(self, **kwargs):
        """Returns paginator data dict, crafted for usage in template."""
        return {
            'page': self.page_contents,
        }

    def data_table_query(self, queryset):
        queryset = self.sort_queryset(queryset, columns=self.columns)
        if self.export_requested():
            self.response = self.do_csv_export(queryset)
        else:
            self.page_contents = self._paginate(queryset)

    def sort_queryset(self, queryset, columns, sort=None):
        """Sorted queryset based on sort param"""
        self.prepare_sortable_columns()
        if columns and queryset:
            if sort is None:
                sort = self.request.GET.get(self.sort_variable_name)
            if sort:
                sort_columns = self.sortable_columns.get(sort.strip('-'))
                if sort_columns:
                    if sort.startswith('-'):
                        sort_columns = '-' + sort_columns
                    queryset = queryset.order_by(sort_columns)
                    self.sort = sort_columns
        return queryset

    def prepare_sortable_columns(self):
        self.sortable_columns = dict(
            (c.field, c.sort_expression) for c in self.columns
            if c.sort_expression
        )

    def _paginate(self, queryset):
        """Internal pagination function"""
        page = self.request.GET.get(self.query_variable_name) or 1
        try:
            self.page_number = int(page)
        except ValueError:
            self.page_number = 1
        self.paginator = Paginator(queryset, self.rows_per_page)
        try:
            page_contents = self.paginator.page(self.page_number)
        except EmptyPage:
            page_contents = self.paginator.page(1)
        return page_contents

    def export_requested(self, *args, **kwargs):
        """Returns True if csv export was requested by the user or
        False in other case
        """
        export = self.request.GET.get(self.export_variable_name)
        return export == 'csv'

    def get_csv_data(self, queryset):
        """Should returns generic rows.
         Override this method in inherited class"""

    def do_csv_export(self, queryset):
        f = StringIO.StringIO()
        data = self.get_csv_data(queryset)
        csvutil.UnicodeWriter(f).writerows(data)
        response = HttpResponse(f.getvalue(), content_type="application/csv")
        response['Content-Disposition'] = 'attachment; filename={}'.format(
            self.csv_file_name)
        return response
