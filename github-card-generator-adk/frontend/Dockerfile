FROM nginx:alpine

# Install gettext for envsubst
RUN apk add --no-cache gettext

# Copy the frontend
COPY index.html /usr/share/nginx/html/index.html.template

# Startup script: inject BACKEND_URL and start nginx
RUN printf '#!/bin/sh\n\
envsubst < /usr/share/nginx/html/index.html.template \
  | sed "s|window.__BACKEND_URL__ = undefined|window.__BACKEND_URL__ = '"'"'${BACKEND_URL}'"'"'|g" \
  > /usr/share/nginx/html/index.html\n\
exec nginx -g "daemon off;"\n' > /docker-entrypoint.sh \
  && chmod +x /docker-entrypoint.sh

EXPOSE 80

CMD ["/docker-entrypoint.sh"]
