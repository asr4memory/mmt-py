FROM nginx:1.26

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d
RUN echo "mmt:\$apr1\$Gr0rRP3e\$xHXLi1F/KyQe9TTYrdIFg/" > /etc/nginx/.htpasswd
