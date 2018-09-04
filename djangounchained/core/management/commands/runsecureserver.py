import os
import ssl
import sys
import datetime

from django.core.servers.basehttp import WSGIRequestHandler, WSGIServer
from django.core.management.base import BaseCommand, CommandError
from django.core.management.commands import runserver

from django.contrib.staticfiles.handlers import StaticFilesHandler

from django.utils._os import upath

class WSGIRequestHandler(WSGIRequestHandler):
    def get_environ(self):
        env = super(WSGIRequestHandler, self).get_environ()
        env['HTTPS'] = 'on'
        return env

class SecureHTTPServer(WSGIServer):
    def __init__(self, address, handler_cls, certificate, key):
        super(SecureHTTPServer, self).__init__(address, handler_cls)
        self.socket = ssl.wrap_socket(self.socket, certfile=certificate, keyfile=key, server_side=True, ssl_version=ssl.PROTOCOL_TLSv1_2, cert_reqs=ssl.CERT_NONE)

def default_ssl_certificates_dir():
    import djangounchained.core.management.commands as module
    mod_path = os.path.dirname(upath(module.__file__))
    ssl_dir = os.path.join(mod_path, "ssl-certificates")
    return ssl_dir

class Command(runserver.Command):
    help = "Replaces the default Django runserver manage command with runsecureserver to serve your Django development server over HTTPS"

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("--certificate", default=os.path.join(default_ssl_certificates_dir(), "development.crt"), help="Path to the certificate"),
        parser.add_argument("--key", default=os.path.join(default_ssl_certificates_dir(), "development.key"), help="Path to the key file"),
        parser.add_argument("--nostatic", dest='use_static_handler', action='store_false', default=None, help="Do not use internal static file handler"),
        parser.add_argument("--static", dest='use_static_handler', action='store_true', help="Use internal static file handler"),

    def get_handler(self, *args, **options):
        """
        Returns the static files serving handler wrapping the default handler,
        if static files should be served. Otherwise just returns the default
        handler.
        """
        handler = super(Command, self).get_handler(*args, **options)
        insecure_serving = options.get('insecure_serving', False)
        if self.use_static_handler(options):
            return StaticFilesHandler(handler)
        return handler

    def use_static_handler(self, options):
        from django.conf import settings
        use_static_handler = options.get('use_static_handler')
        if use_static_handler:
            return True
        if (use_static_handler is None and
            'django.contrib.staticfiles' in settings.INSTALLED_APPS):
            return True
        return False

    def validate_cert_key_files(self, key, cert):
        """
        Check that the certificate and key file exists, and, if they do,
        determine if they can be validated...
        """
        if not os.path.exists(key):
            raise CommandError("Application unable to find the certificate key file {}, please ensure you have included the path to the correct certificate key file".format(key))
        if not os.path.exists(cert):
            raise CommandError("Application unable to find the certificate {}, please ensure you have included the path to the correct SSL certificate".format(cert))


    def inner_run(self, *args, **options):
        key = options.get("key")
        cert = options.get("certificate")
        self.validate_cert_key_files(key, cert)

        from django.conf import settings
        from django.utils import translation

        threading = options.get('use_threading')
        shutdown_message = options.get('shutdown_message', '')
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'

        self.stdout.write("Validating models...\n\n")
        self.check(display_num_errors=True)
        self.details = {
            "started_at": datetime.datetime.now().strftime('%B %d, %Y - %X'),
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": self._raw_ipv6 and '[%s]' % self.addr or self.addr,
            "port": self.port,
            "quit_command": quit_command,
            "cert": cert,
            "key": key
        }

        self.stdout.write((
            "{started_at}\n"
            "Django version {version}, using settings {settings}\n"
            "Starting development server at https://{addr}:{port}/\n"
            "Using SSL certificate: {cert}\n"
            "Using SSL key: {key}\n"
            "Quit the server with {quit_command}.\n"
        ).format( **self.details ))

        translation.activate(settings.LANGUAGE_CODE)

        try:
            handler = self.get_handler(*args, **options)
            server = SecureHTTPServer((self.addr, int(self.port)), WSGIRequestHandler, cert, key)
            server.set_app(handler)
            server.serve_forever()

        except WSGIServerException:
            e = sys.exc_info()[1]
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                13: "You don't have permission to access that port.",
                98: "That port is already in use.",
                99: "That IP address can't be assigned-to.",
            }
            try:
                error_text = ERRORS[e.args[0].args[0]]
            except (AttributeError, KeyError):
                error_text = str(e)
            self.stderr.write("Error: %s" % error_text)
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)
        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write(shutdown_message)
            sys.exit(0)
