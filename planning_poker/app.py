# Ensure eventlet is properly configured for production
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import os
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # In production, use a secure secret key
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active sessions and their participants
sessions = {}

FIBONACCI_POINTS = ['1', '2', '3', '5', '8', '13', '21', '34', '?']

def get_session_state(session_id):
    """Helper function to get the current state of a session"""
    if session_id not in sessions:
        return None
        
    current_participants = [
        {
            'nickname': p['nickname'],
            'is_observer': p['is_observer'],
            'has_voted': sid in sessions[session_id]['current_votes'],
            'is_creator': p.get('is_creator', False)
        }
        for sid, p in sessions[session_id]['participants'].items()
    ]
    
    # Check if all non-observers have voted
    non_observers = [p for p in sessions[session_id]['participants'].values() if not p['is_observer']]
    non_observer_votes = [sid for sid, p in sessions[session_id]['participants'].items() 
                         if not p['is_observer'] and sid in sessions[session_id]['current_votes']]
    all_voted = len(non_observers) > 0 and len(non_observers) == len(non_observer_votes)
    
    # Include revealed votes in session state if they exist
    state = {
        'participants': current_participants,
        'all_voted': all_voted,
        'revealed': sessions[session_id]['revealed']
    }
    
    if sessions[session_id]['revealed']:
        # Format votes as a dictionary keyed by nickname
        votes_dict = {}
        numeric_votes = []
        
        for sid, vote in sessions[session_id]['current_votes'].items():
            nickname = sessions[session_id]['participants'][sid]['nickname']
            votes_dict[nickname] = vote
            
            # Try to convert vote to a number for average calculation
            try:
                numeric_value = float(vote)
                numeric_votes.append(numeric_value)
            except (ValueError, TypeError):
                # Skip non-numeric votes for average calculation
                pass
        
        state['votes'] = votes_dict
        
        # Calculate average if there are numeric votes
        if numeric_votes:
            average = sum(numeric_votes) / len(numeric_votes)
            # Format to one decimal place
            state['average_vote'] = f"{average:.1f}"
        else:
            state['average_vote'] = "N/A"
    
    return state

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create-session', methods=['POST'])
def create_session():
    nickname = request.form.get('nickname')
    if not nickname:
        return 'Nickname is required', 400
    
    session_id = str(uuid.uuid4())[:8]  # Keep the shorter ID format
    sessions[session_id] = {
        'participants': {},
        'current_votes': {},
        'revealed': False,
        'creator_nickname': nickname  # Store the creator's nickname instead of socket ID
    }
    
    session['nickname'] = nickname
    session['is_observer'] = request.form.get('is_observer') == 'true'
    session['is_creator'] = True
    
    return redirect(url_for('poker_room', session_id=session_id))

@app.route('/join/<session_id>', methods=['GET', 'POST'])
def join_session(session_id):
    if session_id not in sessions:
        return 'Session not found', 404
        
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        is_observer = request.form.get('is_observer') == 'true'
        
        if not nickname:
            return 'Nickname is required', 400
            
        session['nickname'] = nickname
        session['is_observer'] = is_observer
        session['is_creator'] = False
        
        return redirect(url_for('poker_room', session_id=session_id))
        
    return render_template('join.html', session_id=session_id)

@app.route('/session/<session_id>')
def poker_room(session_id):
    if session_id not in sessions:
        return 'Session not found', 404
    
    if 'nickname' not in session:
        return redirect(url_for('join_session', session_id=session_id))
    
    return render_template('poker.html', 
                         session_id=session_id, 
                         nickname=session['nickname'],
                         is_observer=session['is_observer'],
                         is_creator=session.get('is_creator', False),
                         points=FIBONACCI_POINTS)

@socketio.on('join')
def on_join(data):
    session_id = data['session_id']
    nickname = session['nickname']
    is_observer = session.get('is_observer', False)
    is_creator = session.get('is_creator', False)
    
    join_room(session_id)
    sessions[session_id]['participants'][request.sid] = {
        'nickname': nickname,
        'is_observer': is_observer,
        'is_creator': is_creator
    }
    
    # If this is the creator joining, store their socket ID
    if is_creator:
        sessions[session_id]['creator_sid'] = request.sid
    
    # Get and broadcast current session state
    session_state = get_session_state(session_id)
    emit('session_state', session_state, room=session_id)
    
    # Also notify about the new user joining
    emit('user_joined', {
        'nickname': nickname,
        'is_observer': is_observer,
        'is_creator': is_creator
    }, room=session_id)

@socketio.on('vote')
def on_vote(data):
    session_id = data['session_id']
    vote = data['vote']
    
    if session_id in sessions and not sessions[session_id]['revealed']:
        sessions[session_id]['current_votes'][request.sid] = vote
        
        # Notify about the vote with the actual vote value
        emit('user_voted', {
            'nickname': session['nickname'],
            'vote': vote
        }, room=session_id)
        
        # Check if all non-observers have voted
        non_observers = [p for p in sessions[session_id]['participants'].values() if not p['is_observer']]
        non_observer_votes = [sid for sid, p in sessions[session_id]['participants'].items() 
                             if not p['is_observer'] and sid in sessions[session_id]['current_votes']]
        all_voted = len(non_observers) > 0 and len(non_observers) == len(non_observer_votes)
        
        # Only emit session_state if all have voted (to update the reveal button)
        if all_voted:
            # Get and broadcast current session state
            session_state = get_session_state(session_id)
            emit('session_state', session_state, room=session_id)

@socketio.on('rescind_vote')
def rescind_vote(data):
    session_id = data['session_id']
    
    if session_id in sessions and not sessions[session_id]['revealed']:
        if request.sid in sessions[session_id]['current_votes']:
            del sessions[session_id]['current_votes'][request.sid]
            
            # Notify about the rescinded vote
            emit('vote_rescinded', {
                'nickname': session['nickname']
            }, room=session_id)
            
            # Get and broadcast current session state to update reveal button state
            session_state = get_session_state(session_id)
            emit('session_state', session_state, room=session_id)

@socketio.on('reveal_votes')
def reveal_votes(data):
    session_id = data['session_id']
    
    print(f"Reveal votes requested for session {session_id}")
    print(f"Current user: {session.get('nickname')}, is_creator: {session.get('is_creator')}")
    
    # Only allow the creator to reveal votes
    if (session_id in sessions and 
        session.get('is_creator') and 
        session.get('nickname') == sessions[session_id]['creator_nickname']):
        
        print(f"Revealing votes for session {session_id}")
        sessions[session_id]['revealed'] = True
        
        # Get the session state which includes the formatted votes and average
        session_state = get_session_state(session_id)
        
        # Prepare votes data for the votes_revealed event
        votes_data = {
            'votes': session_state['votes'],
            'average_vote': session_state['average_vote'],
            'participants': session_state['participants']
        }
        
        print(f"Emitting votes_revealed with data: {votes_data}")
        # Emit votes_revealed event to all participants in the room
        emit('votes_revealed', votes_data, room=session_id)
        
        # Also emit session_state for completeness
        print(f"Emitting session_state with revealed: {session_state['revealed']}")
        emit('session_state', session_state, room=session_id)
    else:
        print(f"Reveal votes request denied. Session exists: {session_id in sessions}")
        if session_id in sessions:
            print(f"Creator nickname: {sessions[session_id]['creator_nickname']}")

@socketio.on('reset_voting')
def reset_voting(data):
    session_id = data['session_id']
    
    # Only allow the creator to reset votes
    if (session_id in sessions and 
        session.get('is_creator') and 
        session.get('nickname') == sessions[session_id]['creator_nickname']):
        
        sessions[session_id]['current_votes'] = {}
        sessions[session_id]['revealed'] = False
        emit('voting_reset', room=session_id)

@socketio.on('disconnect')
def on_disconnect():
    for session_id in sessions:
        if request.sid in sessions[session_id]['participants']:
            nickname = sessions[session_id]['participants'][request.sid]['nickname']
            del sessions[session_id]['participants'][request.sid]
            if request.sid in sessions[session_id]['current_votes']:
                del sessions[session_id]['current_votes'][request.sid]
            leave_room(session_id)
            
            # Get and broadcast current session state
            session_state = get_session_state(session_id)
            if session_state:  # Only emit if the session still exists
                emit('session_state', session_state, room=session_id)
            
            emit('user_left', {'nickname': nickname}, room=session_id)
            break

if __name__ == '__main__':
    socketio.run(app, debug=True)
else:
    # For production deployment
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
