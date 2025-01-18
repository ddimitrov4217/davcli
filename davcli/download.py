# -*- coding: UTF-8 -*-
# vim:ft=python:et:ts=4:sw=4:ai

import os
import re
from datetime import datetime

import click
from pytz import timezone

from davcli import WEBDAV_BASE_URL, click_settings
from davcli.client import DownloadClient


@click.group('download', help='Сваляне на файлове от WebDav', context_settings=click_settings)
@click.argument('davpath')
@click.option('--davhost', help='Базово URL на DaV сървъра', default=WEBDAV_BASE_URL)
@click.option('--user', help='Потребител за достъп по WebDav')
@click.option('--password', help='Парола на потребителя; пита по подразбиране')
@click.option('--proxy', help='Ако има нужда от прокси; формат host:port')
@click.option('--verbose', is_flag=True, help='Отпечатва повече информация за комуникацията')
@click.option('--recursive', is_flag=True, help='Обхожда рекурсивно Dav папките')
@click.option('--pattern', help='Регулярен израз за включване на файла')
@click.option('--swtrac-log-weeks', type=int, help='Брой последните седмици за swtrac log')
@click.pass_context
def cli(ctx, davpath=None, davhost=None, user=None, password=None, proxy=None,
        verbose=None, recursive=None, pattern=None, swtrac_log_weeks=None):
    ctx.ensure_object(dict)
    client = DownloadClient(davpath, davhost)
    client.print_headers = verbose
    client.proxy(proxy)
    ctx.obj['client'] = client

    if swtrac_log_weeks:
        pattern_log = swtrac_log_pattern(last=swtrac_log_weeks)
        pattern_log = f'ssl_request_log_{pattern_log}'
        if pattern is not None:
            pattern = f'({pattern})|({pattern_log})'
        else:
            pattern = pattern_log
        print(pattern)

    ctx.obj['filter'] = recursive, re.compile(pattern) if pattern is not None else None
    ctx.obj['auth'] = user, password


@cli.command('list', help='Извеждна списъка на файловете в DaV директорията')
@click.option('--dest', type=click.Path(dir_okay=True, file_okay=False, exists=True),
              help='Включва маркер дали файла в тази папка е различен')
@click.pass_context
def list(ctx, dest=None):
    client = ctx.obj['client']
    client.auth(*ctx.obj['auth'])

    files = list_files(client, *ctx.obj['filter'], dest=dest)
    fmt1 = '{1:%Y-%m-%d %H:%M} {0:12s} {3:1s} {2:s}'
    fmt2 = '{0:12,d}'

    for size, dttm, filenm, status in files:
        status = status or ''  # noqa: PLW2901
        size = fmt2.format(size) if size is not None else ''  # noqa: PLW2901
        print(fmt1.format(size, dttm, filenm, status))


@cli.command('sync', help='Сваля всички различни или липсващи файлове от WebDav')
@click.argument('dest', type=click.Path(dir_okay=True, file_okay=False, exists=True))
@click.option('--append', is_flag=True, help='Счита че файла само е нараствал (като log)')
@click.pass_context
def sync(ctx, dest=None, append=None):
    client = ctx.obj['client']
    client.auth(*ctx.obj['auth'])

    files = list_files(client, *ctx.obj['filter'], dest=dest)
    for _size, _dttm, filenm, status in files:
        if status is None:
            continue
        destnm = os.path.join(dest, filenm)
        print(filenm, '->', destnm)

        destdir = os.path.dirname(destnm)
        if not os.path.exists(destdir):
            os.makedirs(destdir, exist_ok=True)

        if not append:
            with open(destnm, 'wb') as fout:
                client.download(filenm, fout)
        else:
            if os.path.exists(destnm):
                dsize = os.path.getsize(destnm)
            else:
                dsize = 0

            with open(destnm, 'ab') as fout:
                client.update(filenm, dsize, fout)


def list_files(client, recursive, pattern, dest):
    result = []

    def listpath(bpath=''):
        info = client.path_info(bpath)
        for fi in info:
            isdir, size, dttm, filenm = fi
            if pattern is not None:
                if not pattern.match(filenm):
                    continue

            status = None
            if dest is not None:
                fnm = os.path.join(dest, filenm)
                if os.path.exists(fnm):
                    fsize = int(os.path.getsize(fnm))
                    fdttm = int(os.path.getmtime(fnm))
                    fdttm = datetime.fromtimestamp(fdttm)
                    fdttm = timezone("EET").localize(fdttm)
                    if fdttm < dttm and fsize != size:
                        status = 'B' if size > fsize else 'S'
                else:
                    status = 'N'

            result.append((size, dttm, filenm, status))

        if recursive:
            for isdir, _size, _dttm, filenm in info:
                if isdir and filenm != bpath:
                    listpath(filenm)

    listpath()
    return result


def swtrac_log_pattern(last):
    # регулярен израз за последните няколко седмица
    year, week, weekday = datetime.now().isocalendar()
    patts = []
    pyear = week - last

    if pyear < 0:
        wlist = '|'.join(['%02d' % x for x in range(53+pyear, 53)])
        patts.append('(%d-(%s))' % (year-1, wlist))
        pyear = 0
    wlist = '|'.join(['%02d' % x for x in range(pyear, week+1)])
    patts.append('(%d-(%s))' % (year, wlist))

    return '({})'.format('|'.join(patts))
