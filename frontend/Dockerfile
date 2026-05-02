# CDN-стратегия: никакой сборки. Просто отдаём статику через nginx.
FROM nginx:alpine

# Конфиг nginx с поддержкой SPA-роутинга и инжекцией VITE_API_URL
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
COPY src        /usr/share/nginx/html/src
COPY public     /usr/share/nginx/html/public

EXPOSE 80

# При запуске можно переопределить API_URL через ENV — entrypoint подменит в index.html
ENV SDM_API_URL="http://localhost:8000"
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
