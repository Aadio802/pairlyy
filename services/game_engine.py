"""
Game engines - NO SQL, pure game logic
"""
import random
from typing import Optional, Tuple


# ============ TIC TAC TOE ============
def create_tictactoe_state() -> dict:
    """Create initial tic tac toe state"""
    return {
        'board': [''] * 9,
        'current_symbol': 'X'
    }


def make_tictactoe_move(state: dict, position: int, symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Make a move in tic tac toe.
    Returns (success, winner).
    winner can be 'X', 'O', 'draw', or None (game continues).
    """
    if state['board'][position]:
        return (False, None)
    
    state['board'][position] = symbol
    
    # Check for winner
    winner = check_tictactoe_winner(state['board'])
    if winner:
        return (True, winner)
    
    # Check for draw
    if '' not in state['board']:
        return (True, 'draw')
    
    # Switch symbol
    state['current_symbol'] = 'O' if symbol == 'X' else 'X'
    
    return (True, None)


def check_tictactoe_winner(board: list) -> Optional[str]:
    """Check for tic tac toe winner"""
    winning_combinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]              # Diagonals
    ]
    
    for combo in winning_combinations:
        if board[combo[0]] and board[combo[0]] == board[combo[1]] == board[combo[2]]:
            return board[combo[0]]
    
    return None


# ============ WORD CHAIN ============
EASY_WORDS = [
    "cat", "dog", "sun", "moon", "tree", "book", "love", "home", "star", "bird",
    "fish", "rain", "snow", "wind", "fire", "door", "wall", "road", "park", "lake"
]

HARD_WORDS = [
    "elephant", "computer", "beautiful", "adventure", "wonderful", "mysterious",
    "butterfly", "pineapple", "telescope", "submarine", "chocolate", "dinosaur"
]


def create_wordchain_state(difficulty: str) -> dict:
    """Create initial word chain state"""
    words = EASY_WORDS if difficulty == 'easy' else HARD_WORDS
    initial_word = random.choice(words)
    
    return {
        'words': [initial_word],
        'difficulty': difficulty,
        'used_words': {initial_word.lower()}
    }


def make_wordchain_move(state: dict, word: str) -> Tuple[bool, Optional[str], str]:
    """
    Make word chain move.
    Returns (valid, error_message, last_letter).
    """
    word = word.lower().strip()
    last_word = state['words'][-1]
    
    # Check if word starts with last letter
    if not word.startswith(last_word[-1]):
        return (False, f"Word must start with '{last_word[-1]}'", last_word[-1])
    
    # Check if word already used
    if word in state['used_words']:
        return (False, "Word already used", last_word[-1])
    
    # Check if valid word (basic check - 3+ letters)
    if len(word) < 3:
        return (False, "Word too short (min 3 letters)", last_word[-1])
    
    # Add word
    state['words'].append(word)
    state['used_words'].add(word)
    
    return (True, None, word[-1])


# ============ HANGMAN ============
HANGMAN_WORDS = [
    "python", "telegram", "chatbot", "premium", "sunflower", "streak",
    "garden", "rating", "message", "profile", "keyboard", "button"
]


def create_hangman_state() -> dict:
    """Create initial hangman state"""
    word = random.choice(HANGMAN_WORDS)
    
    return {
        'word': word,
        'guessed_letters': [],
        'wrong_guesses': 0,
        'max_wrong': 6
    }


def make_hangman_guess(state: dict, letter: str) -> Tuple[bool, bool, Optional[str]]:
    """
    Make hangman guess.
    Returns (valid_guess, game_over, result).
    result can be 'won', 'lost', or None.
    """
    letter = letter.lower().strip()
    
    # Validate single letter
    if len(letter) != 1 or not letter.isalpha():
        return (False, False, None)
    
    # Check if already guessed
    if letter in state['guessed_letters']:
        return (False, False, None)
    
    # Add to guessed
    state['guessed_letters'].append(letter)
    
    # Check if letter in word
    if letter not in state['word']:
        state['wrong_guesses'] += 1
        
        # Check if lost
        if state['wrong_guesses'] >= state['max_wrong']:
            return (True, True, 'lost')
    
    # Check if won
    if all(letter in state['guessed_letters'] for letter in state['word']):
        return (True, True, 'won')
    
    return (True, False, None)


def format_hangman_word(state: dict) -> str:
    """Format word with guessed letters"""
    return ' '.join([
        letter if letter in state['guessed_letters'] else '_'
        for letter in state['word']
    ])


def get_next_player(current_player: int, player1: int, player2: int) -> int:
    """Get next player in turn-based game"""
    return player2 if current_player == player1 else player1
