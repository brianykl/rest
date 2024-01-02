from flask import Flask, redirect, url_for, session, request, render_template
from authlib.integrations.flask_client import OAuth
import requests
from config import *
import ipdb

app = Flask(__name__)
app.debug = True
app.secret_key = 'development'

spotify_oauth = OAuth(app)
youtube_oauth = OAuth(app)

spotify = spotify_oauth.register(
    name = 'spotify',
    base_url = 'https://api.spotify.com/v1/',
    request_token_url = None,
    access_token_url = 'https://accounts.spotify.com/api/token',
    access_token_params  = None,
    authorize_url = 'https://accounts.spotify.com/authorize',
    client_id = spotify_client_id,
    client_secret = spotify_client_secret
)

youtube = youtube_oauth.register(
    name = 'youtube',
    base_url = 'https://www.googleapis.com/youtube/v3',
    authorize_url = 'https://accounts.google.com/o/oauth2/auth',
    authorize_params = None,
    access_token_url = 'https://oauth2.googleapis.com/token',
    access_token_params = None,
    client_kwargs = {'scope': 'https://www.googleapis.com/auth/youtube'},
    client_id = youtube_client_id,
    client_secret = youtube_client_secret        
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods = ['GET'])
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
    """
    
    """
    response = spotify.authorize_access_token()
    if response is None or response.get('access_token') is None:
        return 'access denied: reason = {0} error = {1}'.format(
            request.args('error_reason'),
            request.args('error_description')
        )
    session['spotify_token'] = (response['access_token'])
    return redirect(url_for('playlist_selection'))

@app.route('/playlist_selection')
def playlist_selection():
    playlist_list = get_playlists(session['spotify_token']) 
    return render_template('playlist_selection.html', playlists = playlist_list)

@app.route('/playlist_selection/add', methods = ['POST'])
def add():
    playlists = request.form.getlist('selected_playlists')

    migrate_list = []
    for p in playlists:
        playlist = {get_title(session['spotify_token'], p): get_songs(session['spotify_token'], p)}
        migrate_list.append(playlist)
    session['migrate_list'] = migrate_list
    
    return redirect(url_for('migrate'))


@app.route('/playlist_selection/migrate')
def migrate():
    callback = url_for(
        'success', _external = True
    )
    print(callback)
    return youtube.authorize_redirect(callback)

@app.route('/playlist_selection/migrate/success')
def success():
    """
    
    """
    response = youtube.authorize_access_token()
    if response is None or response.get('access_token') is None:
        return 'access denied: reason = {0} error = {1}'.format(
            request.args('error_reason'),
            request.args('error_description')
        )
    session['youtube_token'] = (response['access_token'])
    return redirect(url_for('yay'))

@app.route('/yay')
def yay():
    print(session['migrate_list'])
    return 'woohah'

def get_playlists(access_token):
    response = requests.get('https://api.spotify.com/v1/me/playlists',
                            headers = {'Authorization': f'Bearer {access_token}'})
    if response.status_code == 200:
        playlists = response.json()
        session['playlist_info'] = playlists['items']
        return playlists['items']
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")

def get_title(access_token, playlist_id):
    response = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}',
                            headers = {'Authorization': f'Bearer {access_token}'})
    if response.status_code == 200:
        playlist = response.json()
        return playlist['name']
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")

def get_songs(access_token, playlist_id):
    response = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
                            headers = {'Authorization': f'Bearer {access_token}'})
    track_list = []
    if response.status_code == 200:
        tracks = response.json().get('items', [])
        for t in tracks:
            track_name = t['track']['name']
            track_list.append(track_name)
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")
    return track_list


if __name__ == '__main__':
    app.run(port = 8888)