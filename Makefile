.PHONY: docs test

help:
	@echo "  env          create a development environment using virtualenv"
	@echo "  deps         install dependencies using pip"
	@echo "  clean        remove unwanted files like .pyc's"
	@echo "  lint         check style with flake8"
	@echo "  test         run all your tests using py.test"
	@echo "  docker-test  test with docker image (like CI)"
	@echo "  docker-build Build cs61a/ok-server image"

env:
	easy_install pip && \
	pip install virtualenv && \
	virtualenv . && \
	source ./env/bin/activate && \
	make deps

deps:
	pip install -r requirements.txt

clean:
	./manage.py clean
	-rm *.db

lint:
	flake8 --exclude=env,tests .

test:
	py.test --cov-report term-missing --cov=server tests/

docker-test:
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.test.yml run --rm web

docker-build:
	./manage.py clean
	docker build -t cs61a/ok-server .
