FROM python:3.5

RUN mkdir /code/
WORKDIR /code/

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD . .

CMD ./manage.py server
EXPOSE 5000
