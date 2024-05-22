from flask import Flask, render_template, request, send_file, make_response
from tagger import AudioFileTagger
from registry import ProviderRegistry
from manager import RequestManager, RequestPreferences, TrackSearchContext
from configuration import load_configuration

COOKIE_PREFS_NAME = "musicdll_preferences"
APP_NAME = "Untzine"

# Initialization
conf = load_configuration(APP_NAME)

untzine = Flask(APP_NAME)
untzine.template_folder = "templates"

provider_registry = ProviderRegistry(conf)
provider_registry.load_providers()

# Function to load user context from cookie
def _load_context() -> tuple[RequestPreferences, RequestManager]:
	prefs = RequestPreferences.from_cookie(request.cookies.get(COOKIE_PREFS_NAME, None))
	return prefs, RequestManager(provider_registry, AudioFileTagger(), prefs)

@untzine.get('/')
@untzine.post('/')
def site():

	# Load user preferences from cookie
	user_preferences, request_manager = _load_context()
	update_preferences = False

	# Check if a search request has been made
	search_terms = request.args.get('search_terms', type=str, default=None)

	if search_terms != None and search_terms.strip() != "":

		# Perform request
		search_results = request_manager.search(search_terms)
	else:
		search_results = []

	if request.method == "POST":
		# Update preferences from request
		user_preferences.update_from_form(request.form)
		update_preferences = True

	response = make_response(render_template('base.html', 
				app_name=APP_NAME,
				providers=provider_registry.get_providers(),
				search_results=search_results,
				user_preferences=user_preferences
			))

	if update_preferences:
		response.set_cookie(COOKIE_PREFS_NAME, value=user_preferences.to_cookie(), secure=True, httponly=True)

	return response

@untzine.get('/download')
def download():

	user_preferences, request_manager = _load_context()
	track = request.args.get('track', type=str, default="")

	dll_info = TrackSearchContext.from_url(track, provider_registry)
	filename, content = request_manager.download(dll_info)

	return send_file(content, download_name=filename, as_attachment=True) 

if __name__ == '__main__':
	untzine.run(host='0.0.0.0', port=8000, debug=True)