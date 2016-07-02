FROM python:3.5-alpine

RUN mkdir /code/
WORKDIR /code/

ADD requirements.txt .
RUN apk add --update patch ca-certificates
RUN pip3 install -r requirements.txt

ADD . .

CMD gunicorn -b 0.0.0.0:5000 wsgi:app --workers 3
EXPOSE 5000
