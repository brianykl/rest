from flask import Flask, redirect, url_for, session, request, render_template
from authlib.integrations.flask_client import OAuth
import requests
from config import *
import concurrent.futures
import ipdb

# Initialize Flask application
app = Flask(__name__)
app.debug = True
app.secret_key = 'development'

# OAuth setup for Spotify and YouTube
spotify_oauth = OAuth(app)
youtube_oauth = OAuth(app)

# Register Spotify OAuth with necessary details
spotify = spotify_oauth.register(
    name='spotify',
    base_url='https://api.spotify.com/v1/',
    request_token_url=None,
    access_token_url='https://accounts.spotify.com/api/token',
    access_token_params=None,
    authorize_url='https://accounts.spotify.com/authorize',
    client_id=spotify_client_id,
    client_secret=spotify_client_secret
)

# Register YouTube OAuth with necessary details
youtube = youtube_oauth.register(
    name='youtube',
    base_url='https://www.googleapis.com/youtube/v3',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://oauth2.googleapis.com/token',
    access_token_params=None,
    client_kwargs={'scope': 'https://www.googleapis.com/auth/youtube'},
    client_id=youtube_client_id,
    client_secret=youtube_client_secret        
)

@app.route('/')
def index():
    """
    Route to the home page of the application.
    """
    return render_template('index.html')

@app.route('/spotify_login', methods=['GET'])
def spotify_login():
    """
    Route to handle Spotify login. Redirects to Spotify's authorization page.
    """
    callback = url_for('spotify_authorized', _external=True)
    return spotify.authorize_redirect(callback)

@app.route('/logout')
def logout():
    """
    Route to handle user logout. Clears the session and redirects to the home page.
    """
    session.pop('spotify_token', None)
    print('byebye')
    return redirect(url_for('index'))

@app.route('/spotify_login/authorized')
def spotify_authorized():
    """
    Callback route for Spotify authorization. 
    Retrieves the access token and redirects to YouTube login for authorization.
    """
    response = spotify.authorize_access_token()
    if response is None or response.get('access_token') is None:
        return 'access denied: reason = {0} error = {1}'.format(
            request.args('error_reason'),
            request.args('error_description')
        )
    session['spotify_token'] = (response['access_token'])
    callback = url_for('youtube_login', _external=True)
    return youtube.authorize_redirect(callback)

@app.route('/youtube_login')
def youtube_login():
    """
    Route to handle YouTube login. Retrieves the access token.
    """
    response = youtube.authorize_access_token()
    if response is None or response.get('access_token') is None:
        return 'access denied: reason = {0} error = {1}'.format(
            request.args('error_reason'),
            request.args('error_description')
        )
    session['youtube_token'] = (response['access_token'])
    return redirect(url_for('playlist_selection'))

@app.route('/playlist_selection')
def playlist_selection():
    """
    Displays the playlist selection page after successful login.
    """
    playlist_list = get_playlists(session['spotify_token']) 
    return render_template('playlist_selection.html', playlists=playlist_list)

@app.route('/playlist_selection/add', methods=['POST'])
def add():
    """
    Adds selected playlists to the session for migration.
    """
    playlists = request.form.getlist('selected_playlists')
    session['playlists'] = playlists
    return redirect(url_for('migrate'))

@app.route('/playlist_selection/migrate')
def migrate():
    """
    Initiates the playlist migration process.
    """
    playlists = bundle_playlists
    return render_template('index.html')
    


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
            # print(track_name)
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")
    return track_list

def bundle_playlists():
    migrate_list = {}
    futures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for p in session['playlists']:
            title_future = executor.submit(get_title, session['spotify_token'], p)
            songs_future = executor.submit(get_songs, session['spotify_token'], p)
            futures.append((title_future, songs_future))

    for title_future, songs_future in futures:
        try:
            title = title_future.result()  # Wait for the future result
            songs = songs_future.result()
            migrate_list[title] = songs
        except Exception as e:
            print(f"Error occurred: {e}")
    return migrate_list

def create_playlist(access_token, playlist_name):
    url = f'https://www.googleapis.com/youtube/v3/playlists?part=snippet%2Cstatus&key={youtube_api_key}'
    headers = headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'snippet': {
            f'{playlist_name}': 'Sample playlist created via API',
            # 'description': 'This is a sample playlist description.',
            'tags': ['API call'],
            'defaultLanguage': 'en'
        },
        'status': {
            'privacyStatus': 'private'
        }
    }
    response = requests.post(url, headers, data)
    
    if response.status_code != 400:
        playlist = response.json()
        return playlist['id']
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")

def get_song(access_token, song_name):
    url = 'https://www.googleapis.com/youtube/v3/search'
    params = {
        'part': 'snippet',
        'q': song_name,
        'type': 'video',
        'maxResults': 1,
        'key': access_token
    }
    response = requests.get(url, params=params)

    if response.status_code != 400:
        song = response.json()['items'][0]['id']['videoId']
        return song
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")
    return response.json()
    

def insert_song(access_token, playlist_id, video_id):
    url = f'https://youtube.googleapis.com/youtube/v3/playlistItems?part=snippet&key={youtube_api_key}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'snippet': {
            'playlistId': playlist_id,
            'position': 0,
            'resourceId': {
                'kind': 'youtube#video',
                'videoId': video_id
            }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 400:
        song = response.json()

        return song
    else:
        # Output an error message if something went wrong
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")

def insert_playlists(spotify_playlists):
    migrate_list = {}
    futures = []

    for p in spotify_playlists:
        playlist_id = create_playlist(session['youtube_token'], p)
        for song in spotify_playlists[p]:
            video_id = get_song(session['youtube_token'], song)
            insert_song(session['youtube_token'], playlist_id, video_id)
    return migrate_list



if __name__ == '__main__':
    app.run(port = 8888)





    # with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    #     for p in spotify_playlists:
    #         playlist_id_future = executor.submit(create_playlist, session['youtube_token'], p)
    #         songs_future = executor.submit(insert_song)
    #         futures.append((playlist_id_future, songs_future))

    # for title_future, songs_future in futures:
    #     try:
    #         title = title_future.result()  # Wait for the future result
    #         songs = songs_future.result()
    #         migrate_list[title] = songs
    #     except Exception as e:
    #         print(f"Error occurred: {e}")