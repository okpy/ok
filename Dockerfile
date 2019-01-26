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

# Adding --no-use-pep51 due to build error with pip 19.0.1
# https://gist.github.com/dmulter/38330962002d28533d7dd7c1a70ee4f5
RUN pip3 --timeout=60 install --no-cache-dir --no-use-pep51 -r requirements.txt

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
