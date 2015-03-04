ZIP_NAME=../GAE.zip

setup:
	curl https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.18.zip -o $ZIP_NAME
	unzip -q $ZIP_NAME
	export GAE_SDK=/home/deploy_bot/google_appengine
	rm -f $ZIP_NAME
	sudo apt-get install nodejs

update:
	bower install
	appcfg.py update .

