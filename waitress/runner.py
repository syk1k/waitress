##############################################################################
#
# Copyright (c) 2013 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Command line runner.
"""

from __future__ import print_function

import getopt
import os.path
import re
import sys

from waitress import serve
from waitress.adjustments import Adjustments

HELP = """\
Usage:

    %(name)s [OPTS] MODULE:OBJECT

Standard options:

    --help
        Show this information.

    --call
        Call the given object to get the WSGI application.

    --host=ADDR
        Hostname or IP address on which to listen, default is '0.0.0.0',
        which means "all IP addresses on this host".

    --port=PORT
        TCP port on which to listen, default is '8080'

    --unix-socket=PATH
        Path of Unix socket. If a socket path is specified, a Unix domain
        socket is made instead of the usual inet domain socket.

        Not available on Windows.

    --unix-socket-perms=PERMS
        Octal permissions to use for the Unix domain socket, default is
        '600'.

    --url-scheme=STR
        Default wsgi.url_scheme value, default is 'http'.

    --ident=STR
        Server identity used in the 'Server' header in responses. Default
        is 'waitress'.

Tuning options:

    --threads=INT
        Number of threads used to process application logic, default is 4.

    --backlog=INT
        Connection backlog for the server. Default is 1024.

    --recv-bytes=INT
        Number of bytes to request when calling socket.recv(). Default is
        8192.

    --send-bytes=INT
        Number of bytes to send to socket.send(). Default is 18000.
        Multiples of 9000 should avoice partly-filled TCP packets.

    --outbuf-overflow=INT
        A temporary file should be created if the pending output is larger
        than this. Default is 1048576 (1MB).

    --inbuf-overflow=INT
        A temporary file should be created if the pending input is larger
        than this. Default is 524288 (512KB).

    --connection-limit=INT
        Stop creating new channelse if too many are already active.
        Default is 100.

    --cleanup-interval=INT
        Minimum seconds between cleaning up inactive channels. Default
        is 30. See '--channel-timeout'.

    --channel-timeout=INT
        Maximum number of seconds to leave inactive connections open.
        Default is 120. 'Inactive' is defined as 'has recieved no data
        from the client and has sent no data to the client'.

    --[no-]log-socket-errors
        Toggle whether premature client disconnect tracepacks ought to be
        logged. On by default.

    --max-request-header-size=INT
        Maximum size of all request headers combined. Default is 262144
        (256KB).

    --max-request-body-size=INT
        Maximum size of request body. Default is 1073741824 (1GB).

    --[no-]expose-tracebacks
        Toggle whether to expose tracebacks of unhandled exceptions to the
        client. Off by default.

    --asyncore-loop-timeout=INT
        The timeout value in seconds passed to asyncore.loop(). Default is 1.
"""

RUNNER_PATTERN = re.compile(r"""
    ^
    (?P<module>
        [a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*
    )
    :
    (?P<object>
        [a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*
    )
    $
    """, re.I | re.X)

def match(obj_name):
    matches = RUNNER_PATTERN.match(obj_name)
    if not matches:
        raise ValueError("Malformed application '%s'" % obj_name)
    return matches.group('module'), matches.group('object')

def resolve(module_name, object_name):
    """Resolve a named object in a module."""
    obj = __import__(module_name, fromlist=[object_name.split('.', 1)[0]])
    for segment in object_name.split('.'):
        obj = getattr(obj, segment)
    return obj

def show_help(stream, name, error=None):  # pragma: no cover
    if error is not None:
        print('Error: %s\n' % error, file=stream)
    print(HELP % {'name': name}, file=stream)

def run(argv=sys.argv, _serve=serve):
    """Command line runner."""
    name = os.path.basename(argv[0])

    try:
        kw, args = Adjustments.parse_args(argv[1:])
    except getopt.GetoptError as exc:
        show_help(sys.stderr, name, exc.msg)
        return 1

    if kw['help']:
        show_help(sys.stdout, name)
        return 0

    if len(args) != 1:
        show_help(sys.stderr, name, 'Specify one application only')
        return 1

    try:
        module, obj_name = match(args[0])
    except ValueError, exc:
        show_help(sys.stderr, name, exc.message)
        return 1

    # Get the WSGI function.
    try:
        app = resolve(module, obj_name)
    except ImportError:
        show_help(sys.stderr, name, "Bad module '%s'" % module)
        return 1
    except AttributeError:
        show_help(sys.stderr, name, "Bad object name '%s'" % obj_name)
        return 1
    if kw['call']:
        app = app()

    # These arguments are specific to the runner, not waitress itself.
    del kw['call'], kw['help']

    _serve(app, **kw)
    return 0
