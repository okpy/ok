FROM python:3.5-alpine

RUN apk add --update patch ca-certificates nginx perl;

RUN mkdir /code/
WORKDIR /code/

ADD requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

ADD . .

RUN mv docker/nginx/nginx.conf /etc/nginx/nginx.conf
RUN mv docker/nginx/default.conf /etc/nginx/conf.d/default.conf

RUN ./manage.py assets build

CMD nginx && \
    env PYTHONPATH=$PYTHONPATH:$PWD gunicorn \
        --logger-class server.logging.gunicorn.Logger \
        --timeout 60 \
        --bind unix:/tmp/server.sock \
        --workers 3 \
        wsgi:app

RUN rm -rf /var/cache/apk/*

EXPOSE 5000
