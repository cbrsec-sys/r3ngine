FROM postgres:16-alpine

# Custom configuration — raises max_connections for concurrent Temporal
# activity threads and tunes shared_buffers for the container memory budget.
COPY postgresql.conf /etc/postgresql/postgresql.conf
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
