import random
import string
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-later'
socketio = SocketIO(app, cors_allowed_origins="*")

# Board configuration (Head/Bottom -> Tail/Top)
SNAKES = {16: 6, 47: 26, 49: 11, 56: 53, 62: 19, 64: 60, 87: 24, 93: 73, 95: 75, 98: 78}
LADDERS = {1: 38, 4: 14, 9: 31, 21: 42, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}

# In-memory storage for active game rooms
rooms = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_room')
def on_create():
    room = generate_room_code()
    rooms[room] = {
        'players': {request.sid: {'num': 1, 'pos': 0, 'name': 'Player 1 (Red)'}},
        'turn': 1,
        'status': 'waiting'
    }
    join_room(room)
    emit('room_joined', {'room': room, 'player_num': 1, 'state': rooms[room]})

@socketio.on('join_room')
def on_join(data):
    room = data.get('room', '').upper().strip()
    if room not in rooms:
        emit('error_msg', {'msg': 'Room not found!'})
        return
    if len(rooms[room]['players']) >= 2:
        emit('error_msg', {'msg': 'Room is already full!'})
        return

    rooms[room]['players'][request.sid] = {'num': 2, 'pos': 0, 'name': 'Player 2 (Blue)'}
    rooms[room]['status'] = 'playing'
    join_room(room)
    emit('room_joined', {'room': room, 'player_num': 2, 'state': rooms[room]})
    emit('game_update', {'state': rooms[room], 'log': 'Player 2 joined! Game started.'}, to=room)

@socketio.on('roll_dice')
def on_roll(data):
    room = data.get('room')
    if room not in rooms or rooms[room]['status'] != 'playing':
        return

    game = rooms[room]
    player = game['players'].get(request.sid)
    if not player or player['num'] != game['turn']:
        return  # Not this player's turn

    dice = random.randint(1, 6)
    old_pos = player['pos']
    new_pos = old_pos + dice
    log_msg = f"{player['name']} rolled a {dice}."

    if new_pos > 100:
        new_pos = old_pos
        log_msg += " Overshot 100! Stayed put."
    else:
        if new_pos in LADDERS:
            log_msg += f" Climbed a ladder from {new_pos} to {LADDERS[new_pos]}!"
            new_pos = LADDERS[new_pos]
        elif new_pos in SNAKES:
            log_msg += f" Bitten by a snake at {new_pos}! Slid down to {SNAKES[new_pos]}."
            new_pos = SNAKES[new_pos]

    player['pos'] = new_pos

    if new_pos == 100:
        game['status'] = 'finished'
        log_msg = f"🎉 {player['name']} wins the game!"
    else:
        game['turn'] = 2 if game['turn'] == 1 else 1

    emit('game_update', {'state': game, 'log': log_msg, 'dice': dice}, to=room)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=8000)
