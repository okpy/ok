FROM python:3.5-alpine

RUN apk add --update \
    supervisor \
    patch \
    ca-certificates \
    nginx \
    perl \
    musl-dev \
    openssl-dev \
    libffi-dev \
    python-dev \
    gcc

RUN mkdir /code/
WORKDIR /code/

ADD requirements.txt .

RUN pip3 --timeout=60 install --no-cache-dir -r requirements.txt

RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

ADD . .

RUN mv docker/nginx/nginx.conf /etc/nginx/nginx.conf && \
    mv docker/nginx/default.conf /etc/nginx/conf.d/default.conf && \
    mv docker/supervisor.conf /etc/supervisor.conf && \
    mv docker/wait-for /wait-for

RUN ./manage.py assets build

RUN rm -rf /var/cache/apk/*

ENV SQL_CA_CERT=/code/BaltimoreCyberTrustRoot.crt.pem
ENV SCRIPT_NAME=
ENV GUNICORN_WORKERS=3
ENV GUNICORN_TIMEOUT=60
ENV OKPY_LOG_LEVEL=INFO

EXPOSE 5000

CMD ["/code/docker/run-supervisor.sh"]
