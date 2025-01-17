# -*- coding: UTF-8 -*-
# vim:ft=python:et:ts=4:sw=4:ai

import click

from davcli.download import cli as cli_download
from davcli.mirror import cli as cli_mirror


@click.group('tools', help='Инструменти за използване на WebDav')
def cli_tools():
    pass


cli_tools.add_command(cli_download)
cli_tools.add_command(cli_mirror)


if __name__ == '__main__':
    cli_tools()
