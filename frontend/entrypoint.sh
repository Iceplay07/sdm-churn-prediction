#!/bin/sh
# Инжектируем SDM_API_URL в index.html перед запуском nginx
sed -i \
  -e "s|<head>|<head>\n  <script>window.__SDM_API_URL__='${SDM_API_URL}';window.__SDM_FALLBACK_ON_ERROR__=true;</script>|" \
  /usr/share/nginx/html/index.html
exec nginx -g "daemon off;"
