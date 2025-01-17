# -*- coding: UTF-8 -*-
# vim:ft=python:et:ts=4:sw=4:ai

import os
from datetime import datetime
from getpass import getpass
import sqlite3
import click

from . import WEBDAV_BASE_URL, click_settings
from . client import MirrorClient


@click.command('mirror', help='Mirror на папка към WebDav', context_settings=click_settings)
@click.argument('path', type=click.Path(dir_okay=True, file_okay=False, exists=True))
@click.argument('davpath')
@click.option('--upload', '-r', is_flag=True, help='Реално качва променените файлове')
@click.option('--target', '-t', default=WEBDAV_BASE_URL,
              help='Базово URL зад което се прилага devpath префикса')
@click.option('--user', '-u', help='Потребител за достъп по webdav')
@click.option('--password', help='Парола на потребителя; пита по подразбиране')
@click.option('--verbose', '-v', is_flag=True, help='Отпечатва повече информация за комуникацията')
@click.option('--proxy', help='Ако има нужда от прокси; формат host:port')
@click.option('--no-delete-empty', is_flag=True, help='Да не трие празните директории')
def cli(path=None, davpath=None, upload=None, target=None, user=None, password=None,
        verbose=None, proxy=None, no_delete_empty=None):
    os.chdir(path)
    mark_action(no_delete_empty)

    if upload:
        client = MirrorClient(davpath, target)
        client.print_headers = verbose
        if password is None:
            password = getpass('Password for %s: ' % user)
        client.auth(user, password)
        client.proxy(proxy)
    else:
        client = None

    process_action(client)


def open_mirror_db(dbname=".webdav_mark_db"):
    class wrapped:
        def __enter__(self):
            self.con = sqlite3.connect(dbname)
            self.crs = self.con.cursor()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.con.close()

        def action(self, fname, action):
            self.crs.execute(
                "update mirror set action = ?, tstamp = current_timestamp "
                "where fname = ?", (action, fname, ))
            self.con.commit()

        def delete(self, fname):
            self.crs.execute("delete from mirror where fname = ?", (fname, ))
            self.con.commit()

        def create(self, fname, size, mtime):
            self.crs.execute(
                "insert into mirror (fname, size, mtime, action, tstamp) "
                "values (?, ?, ?, 'UPLOAD', current_timestamp)",
                (fname, size, mtime))
            self.con.commit()

        def done(self, fname, size, mtime):
            self.crs.execute(
                "update mirror set size = ?, mtime = ?, action = null, tstamp = current_timestamp "
                "where fname = ?", (size, mtime, fname))
            self.con.commit()

    if not os.path.exists(dbname):
        with wrapped() as eng:
            eng.con.execute("""
            create table mirror (
                size   long not null,
                mtime  long not null,
                action varchar(10),
                tstamp timestamp not null,
                fname  varchar(2048) not null primary key)""")

    return wrapped()


def mark_action(no_delete_empty=False):
    with open_mirror_db() as eng:
        c = eng.con.cursor()

        # (0) изчистване на папите за истриване
        c.execute("delete from mirror where action = 'DELETE' and fname like '%/'")
        eng.con.commit()

        # (1) проверка за нови и променени файлове
        for root, dirs, files in os.walk('.'):
            for name in files:
                if name.startswith('.'):
                    continue

                fnm = os.path.join(root, name)
                fnm = fnm[2:]
                fnm = fnm.replace('\\', '/')
                size, mtime = int(os.path.getsize(fnm)), int(os.path.getmtime(fnm))

                res = c.execute("select size, mtime, action from mirror where fname = ?", (fnm,))
                info = res.fetchone()

                if info is None:
                    eng.create(fnm, size, mtime)
                else:
                    size_last, mtime_last, action = info
                    if size_last != size or mtime_last != mtime or action == 'DELETE':
                        eng.action(fnm, 'UPLOAD')

        # (2) проверка за изтрити файлове
        del_paths = set()
        for fnm, in c.execute("select fname from mirror").fetchall():
            if not os.path.exists(fnm):
                eng.action(fnm, 'DELETE')
                eng.con.commit()
                del_paths.add(os.path.dirname(fnm))

        # (3) Напълно празните директории се изтриват
        if not no_delete_empty:
            for dpath in del_paths:
                if not dpath:
                    continue
                dpath = '%s/' % dpath
                res = c.execute("select 1 from mirror where fname like ?||'%'"
                                "    and (action is null or action != 'DELETE')",
                                (dpath,))
                if res.fetchone() is None:
                    res = c.execute("select 1 from mirror where fname = ?", (dpath,))
                    if res.fetchone() is None:
                        eng.create(dpath, 0, datetime.now())
                    eng.action(dpath, 'DELETE')


def process_action(client):
    with open_mirror_db() as eng:
        c = eng.con.cursor()
        res = c.execute(
                "select fname, action, size from mirror "
                "where action is not null "
                "order by action desc, fname desc")

        for fnm, action, size in res.fetchall():
            print('{0:s} {1:,d} KB {2:s}'.format(action, size//1024, fnm))

            if client is None:
                continue

            if action == 'UPLOAD':
                if client.mkcol(fnm) and client.put(fnm):
                    size, mtime = int(os.path.getsize(fnm)), int(os.path.getmtime(fnm))
                    eng.done(fnm, size, mtime)
            else:
                if client.delete(fnm):
                    eng.delete(fnm)

            print()
