# -*- coding: UTF-8 -*-
# vim:ft=python:et:ts=4:sw=4:ai

import click
from os import environ

click_settings = {}

if click.__version__ >= '8':
    click_settings['show_default'] = True

WEBDAV_BASE_URL = environ.get('DAVCLI_WEBDAV_BASE_URL')
