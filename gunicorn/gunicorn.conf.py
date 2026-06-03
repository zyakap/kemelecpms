import multiprocessing

# Server socket
bind = "unix:/run/gunicorn/kemelecpms.sock"
backlog = 2048

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Process naming
proc_name = "kemelecpms"

# Logging
accesslog = "/var/log/gunicorn/kemelecpms_access.log"
errorlog = "/var/log/gunicorn/kemelecpms_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Server mechanics
daemon = False
pidfile = "/run/gunicorn/kemelecpms.pid"
user = "www-data"
group = "www-data"
umask = 0o007

# Environment
raw_env = [
    "DJANGO_SETTINGS_MODULE=config.settings.production",
]

# Reload on code change (development only — comment out in production)
# reload = True

# Max requests per worker (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Preload application for faster worker spawning
preload_app = True
