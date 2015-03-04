zip_name = ../../GAE.zip
gae_location = /home/deploy_bot

setup:
	curl https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.18.zip -o $(zip_name)
	unzip -q $(zip_name) -d $(gae_location)
	export GAE_SDK=$(gae_location)/google_appengine
	rm -f $(zip_name)

update:
	bower install
	appcfg.py --oauth2 update .

