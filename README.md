# Planning Poker

A simple, real-time Planning Poker application for Scrum teams. This app allows team members to participate in story point estimation sessions remotely.

## Features

- Create separate sessions for different teams
- Join as a participant or observer
- Real-time voting using Fibonacci sequence
- No authentication required - just pick a nickname
- Reveal votes only when everyone has voted
- Reset voting for new stories

## Installation

1. Create and activate a virtual environment using `uv`:
```bash
uv venv
source .venv/bin/activate  # On Unix-like systems
# or
.venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
uv pip install -e .
```

## Running the Application

1. Start the server:
```bash
python -m planning_poker.app
```

2. Open your browser and navigate to `http://localhost:5000`

3. Create a new session by entering your nickname

4. Share the session URL with your team members

## Running Tests

```bash
pytest tests/
```

## Usage

1. Create a new session by entering your nickname
2. Choose whether you want to join as an observer or participant
3. Share the session URL with your team
4. Participants can select their story point estimates
5. Click "Reveal Votes" to show everyone's votes
6. Use "Reset" to start a new round

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request