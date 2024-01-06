import app
import pytest

def test_create_playlist(mocker):
    # Mock the response of the requests.post method
    mock_response = mocker.Mock(status_code=200, json=lambda: {'id': '12345'})
    mocker.patch('app.requests.post', return_value=mock_response)

    # Call the function
    result = app.create_playlist('dummy_access_token', 'Test Playlist')

    # Assert that the result is as expected
    assert result == '12345'

def test_get_song(mocker):
    mock_response = mocker.Mock(status_code=200, json=lambda: {'items': [{'id': {'videoId': 'abcd1234'}}]})
    mocker.patch('app.requests.get', return_value=mock_response)

    result = app.get_song('dummy_access_token', 'Test Song')

    assert result == 'abcd1234'

def test_insert_song(mocker):
    mock_response = mocker.Mock(status_code=200, json=lambda: {'id': 'song123'})
    mocker.patch('app.requests.post', return_value=mock_response)

    result = app.insert_song('dummy_access_token', 'playlist123', 'video123')

    # Depending on what insert_song returns, assert the expected result
    assert result == {'id': 'song123'}