# Use the latest Redis stack server as base image
FROM redis/redis-stack-server:latest

# Create the home directory for the new non-root user.
RUN mkdir -p /home/nonroot

# Create a non-root user so our program doesn't run as root.
RUN useradd -d /home/nonroot -s /bin/bash nonroot

COPY ./backend/redis_db_setup/entrypoint.sh /entrypoint.sh

RUN chmod a+rx /entrypoint.sh

USER nonroot

# Expose the Redis port
EXPOSE 6379


HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["/entrypoint.sh"]