FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends tor && \
    rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 9050 9051

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
