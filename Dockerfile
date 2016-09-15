FROM python:3.5-alpine

RUN mkdir /code/
WORKDIR /code/

ADD requirements.txt .
RUN apk add --update patch ca-certificates nginx && rm -rf /var/cache/apk/*

RUN mkdir -p /tmp/nginx/client-body

COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

RUN pip3 install -r requirements.txt

ADD . .

RUN ./manage.py assets build

CMD nginx; gunicorn -b 0.0.0.0:5000 wsgi:app --workers 3

EXPOSE 5000
