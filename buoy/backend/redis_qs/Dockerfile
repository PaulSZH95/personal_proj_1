FROM redis:alpine3.18

# Create the home directory for the new non-root user.
RUN mkdir -p /home/nonroot
# Create a non-root user so our program doesn't run as root.
RUN adduser -S -h /home/nonroot nonroot

# Copy the custom Redis configuration file into the container
COPY ./backend/redis_qs/redis.conf /usr/local/etc/redis/redis.conf

RUN chmod a+rx /usr/local/etc/redis/redis.conf

# Specify the custom configuration file
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]

# Declare the Redis data directory as a volume
VOLUME /data

# # Additional volume for temporary files if needed
# VOLUME /home/nonroot/tmp

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD redis-cli ping

USER nonroot

EXPOSE 6379