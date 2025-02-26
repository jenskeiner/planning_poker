import pytest
from planning_poker.app import app, sessions

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Planning Poker' in response.data

def test_create_session_without_nickname(client):
    response = client.post('/create-session', data={})
    assert response.status_code == 400
    assert b'Nickname is required' in response.data

def test_create_session_with_nickname(client):
    response = client.post('/create-session', data={'nickname': 'TestUser'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Planning Poker - Session' in response.data

def test_join_invalid_session(client):
    response = client.get('/session/invalid-id')
    assert response.status_code == 404
    assert b'Session not found' in response.data

def test_fibonacci_sequence():
    from planning_poker.app import FIBONACCI_POINTS
    expected = ['1', '2', '3', '5', '8', '13', '21', '34', '?']
    assert FIBONACCI_POINTS == expected

def test_vote_and_rescind(client):
    with client.session_transaction() as sess:
        sess['nickname'] = 'TestUser'
        sess['is_observer'] = False
    
    # Create a session
    response = client.post('/create-session', data={'nickname': 'TestUser'})
    session_id = response.location.split('/')[-1]
    
    # Create a test client for Socket.IO
    socket_client = app.socketio.test_client(app)
    
    # Join the session
    socket_client.emit('join', {'session_id': session_id})
    
    # Cast a vote
    socket_client.emit('vote', {'session_id': session_id, 'vote': '5'})
    assert session_id in sessions
    assert socket_client.sid in sessions[session_id]['current_votes']
    assert sessions[session_id]['current_votes'][socket_client.sid] == '5'
    
    # Rescind the vote
    socket_client.emit('rescind_vote', {'session_id': session_id})
    assert socket_client.sid not in sessions[session_id]['current_votes']
    
    # Try to rescind when votes are revealed (should not work)
    socket_client.emit('reveal_votes', {'session_id': session_id})
    socket_client.emit('vote', {'session_id': session_id, 'vote': '8'})
    socket_client.emit('rescind_vote', {'session_id': session_id})
    assert socket_client.sid in sessions[session_id]['current_votes']
    assert sessions[session_id]['current_votes'][socket_client.sid] == '8'

def test_vote_rescinding(client):
    with client.session_transaction() as sess:
        sess['nickname'] = 'TestUser'
        sess['is_observer'] = False
    
    # Create a session
    response = client.post('/create-session', data={'nickname': 'TestUser'})
    session_id = response.location.split('/')[-1]
    
    # Create a test client for Socket.IO
    socket_client = app.socketio.test_client(app)
    
    # Join the session
    socket_client.emit('join', {'session_id': session_id})
    
    # Cast a vote
    socket_client.emit('vote', {'session_id': session_id, 'vote': '5'})
    assert session_id in sessions
    assert socket_client.sid in sessions[session_id]['current_votes']
    assert sessions[session_id]['current_votes'][socket_client.sid] == '5'
    
    # Rescind the vote
    socket_client.emit('rescind_vote', {'session_id': session_id})
    assert socket_client.sid not in sessions[session_id]['current_votes']
    
    # Cast another vote
    socket_client.emit('vote', {'session_id': session_id, 'vote': '8'})
    assert session_id in sessions
    assert socket_client.sid in sessions[session_id]['current_votes']
    assert sessions[session_id]['current_votes'][socket_client.sid] == '8'
    
    # Rescind the vote again
    socket_client.emit('rescind_vote', {'session_id': session_id})
    assert socket_client.sid not in sessions[session_id]['current_votes']
