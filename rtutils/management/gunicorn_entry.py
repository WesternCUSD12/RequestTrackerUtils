import sys
from gunicorn.app.wsgiapp import run


def main():
    sys.argv = [
        "gunicorn",
        "--bind",
        "0.0.0.0:5000",
        "--workers",
        "4",
        "--timeout",
        "120",
        "--access-logfile",
        "/var/lib/request-tracker-utils/logs/access.log",
        "--error-logfile",
        "/var/lib/request-tracker-utils/logs/error.log",
        "--log-level",
        "info",
        "rtutils.wsgi:application",
    ]
    run()
