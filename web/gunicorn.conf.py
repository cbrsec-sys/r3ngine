import multiprocessing

# Bind — nginx reverse-proxies here
bind = "0.0.0.0:8000"

# UvicornWorker provides full ASGI support: HTTP + WebSocket (Django Channels)
worker_class = "uvicorn.workers.UvicornWorker"

# (2 × CPU cores) + 1, capped at 4 for the container memory budget
workers = min((2 * multiprocessing.cpu_count()) + 1, 4)

# Async workers are single-threaded; each worker runs its own event loop
threads = 1

backlog = 512
timeout = 120           # Kill hung worker after 120s
graceful_timeout = 30   # Allow in-flight requests to finish on SIGTERM
keepalive = 5

accesslog = "-"         # stdout → Docker log aggregation
errorlog = "-"          # stderr → Docker log aggregation
loglevel = "info"

proc_name = "r3ngine"

# Trust X-Forwarded-For from nginx
forwarded_allow_ips = "*"
