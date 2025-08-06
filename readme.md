# Untzine
Music downloader as a simple website to host.  
Use multiple providers to search and download music from.
For the moment, only spotify provider is available.

## Get started
The app is packaged as a docker application, available at `https://hub.docker.com/repository/docker/unepoule/untzine`.

Launch the app with docker: 
> docker run -p \<port>:80 unepoule/untzine

You can then access it with your browser at `http://localhost:<port>`.

If you want to launch as a python script, see the [development](#development) section.

You will need to configure some providers to download audio files.

### Configuration
The app use a configuration file or environment variables to configure itself.  
See `configuration.template.json` for a json configuration file example.  
Each configuration value can be configured by json or with an env variable:
- __JSON:__ ````{"provider":{"conf1": "value"}}````
- __ENV:__ `UNTZINE__PROVIDER__CONF1=value`

Environment variables are prioritary and will erase any JSON configuration value.

Here is a list of configuration values available:

| Description | JSON | ENV | example |
|-------------|------|-----|---------|
| file path to store and use valid session once logged in | spotify.login_session_save_path | UNTZINE__SPOTIFY__LOGIN_SESSION_SAVE_PATH | spotify_session.json
| session file as base64 directly, prioritary if configured. You can put the session file content here once logged in | spotify.session  |  UNTZINE__SPOTIFY__SESSION   | aGVoZWhlbm90aGluZ3NlY3JldGhlcmU= |
| Deezer arl exported from cookies | deezer.arl  |  UNTZINE__DEEZER__ARL   | 1sVE1tWmZNbXB1YmtsdFJIQmhObVUxZDNSMU9Ia |

## Development

Clone the git project:
> git clone git@github.com:SubtleWhale/untzine.git

Create a python virtual environment and install dependancies:

> python -m venv .venv  
> pip install -r requirements.txt

Configure the app with a config file if needed, or with the env variables. You can use `configuration.template.json` for inspiration.

Launch the app:
> python app/untzine.py <configuration_file>