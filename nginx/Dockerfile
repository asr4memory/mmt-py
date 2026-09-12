FROM nginx:1.29

# The worker processes run as the nginx user. Its uid and gid are set to those
# of the app user in the app image (APP_UID in app/Dockerfile) so nginx can
# read the user files the app writes with mode 0640, without the files being
# readable by every other uid on the host.
ARG APP_UID=999

RUN groupmod -g "$APP_UID" nginx && \
    usermod -u "$APP_UID" -g "$APP_UID" nginx && \
    chown -R nginx:nginx /var/cache/nginx

# The image's entrypoint renders the template into /etc/nginx/conf.d at
# startup, substituting the MMT_* variables.
COPY default.conf.template /etc/nginx/templates/
