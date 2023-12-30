from flask import Flask, redirect, url_for, session, request, render_template
from authlib.integrations.flask_client import OAuth
import requests
from config import *
import ipdb

app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

spotify = oauth.register(
    name = 'spotify',
    base_url = 'https://api.spotify.com/v1/',
    request_token_url = None,
    access_token_url = 'https://accounts.spotify.com/api/token',
    access_token_params  = None,
    authorize_url = 'https://accounts.spotify.com/authorize',
    client_id = spotify_client_id,
    client_secret = spotify_client_secret
)

@app.route('/')
def index():
    return 'welcome to my app'

@app.route('/login')
def login():
    callback = url_for(
        'authorized', _external = True
    )
    return spotify.authorize_redirect(callback)

@app.route('/logout')
def logout():
    session.pop('oauth_token', None)
    print('byebye')
    return redirect(url_for('index'))

@app.route('/login/authorized')
def authorized():
    response = spotify.authorize_access_token()
    if response is None or response.get('access_token') is None:
        return 'access denied: reason = {0} error = {1}'.format(
            request.args('error_reason'),
            request.args('error_description')
        )
    session['oauth_token'] = (response['access_token'])
    print("authorized")
    return redirect(url_for('playlist_selection'))

@app.route('/playlist_selection')
def playlist_selection():
    playlist_list = get_user_playlists(session['oauth_token'])
    # ipdb.set_trace() 
    return render_template('playlist_selection.html', playlists = playlist_list)


def get_name(access_token):
    response = requests.get('https://api.spotify.com/v1/me', 
                            headers = {'Authorization': f'Bearer {access_token}'})
    if response.status_code == 200:
    # Parse the JSON response
        artist_data = response.json()
        print(artist_data['display_name'])
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")

def get_user_playlists(access_token):
    response = requests.get('https://api.spotify.com/v1/me/playlists',
                            headers = {'Authorization': f'Bearer {access_token}'})
    if response.status_code == 200:
        playlists = response.json()
        return playlists['items']
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")

if __name__ == '__main__':
    app.run(port = 8888)