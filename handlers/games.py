"""
Game handlers - NO SQL, uses db.games and services.game_engine
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.users import get_partner_id, is_premium
from db.matchmaking import get_chat_id
from db.games import create_game, get_active_game, update_game_state, end_game
from db.sunflowers import get_sunflower_balance, add_sunflowers, deduct_sunflowers_smart
from services.game_engine import (
    create_tictactoe_state, make_tictactoe_move, check_tictactoe_winner,
    create_wordchain_state, create_hangman_state, get_next_player
)
from config import settings

router = Router()


@router.message(Command("game"))
async def cmd_game(message: Message):
    """Show game menu"""
    user_id = message.from_user.id
    partner_id = await get_partner_id(user_id)
    
    if not partner_id:
        await message.answer("You must be in a chat to play games. Use /find first!")
        return
    
    # Check premium
    if not await is_premium(user_id):
        await message.answer(
            "🎮 Games are a Premium feature!\n\n"
            "Use /premium to upgrade or buy temp premium with sunflowers."
        )
        return
    
    # Check if game already active
    chat_id = await get_chat_id(user_id)
    active_game = await get_active_game(chat_id)
    
    if active_game:
        await message.answer("A game is already in progress!")
        return
    
    # Show game menu
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 Tic Tac Toe", callback_data="game_menu:tictactoe")
    builder.button(text="📝 Word Chain (Easy)", callback_data="game_menu:wordchain_easy")
    builder.button(text="📝 Word Chain (Hard)", callback_data="game_menu:wordchain_hard")
    builder.button(text="🔤 Hangman", callback_data="game_menu:hangman")
    builder.adjust(1)
    
    await message.answer(
        "🎮 Choose a game to play:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("game_menu:"))
async def game_menu_callback(callback: CallbackQuery):
    """Handle game selection"""
    game_type = callback.data.split(":")[1]
    
    # Show bet options
    builder = InlineKeyboardBuilder()
    builder.button(text="No bet", callback_data=f"game_bet:{game_type}:0")
    builder.button(text="50 🌻", callback_data=f"game_bet:{game_type}:50")
    builder.button(text="100 🌻", callback_data=f"game_bet:{game_type}:100")
    builder.button(text="200 🌻", callback_data=f"game_bet:{game_type}:200")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "Choose bet amount:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("game_bet:"))
async def game_bet_callback(callback: CallbackQuery):
    """Handle bet selection and send invitation"""
    parts = callback.data.split(":")
    game_type = parts[1]
    bet_amount = int(parts[2])
    
    user_id = callback.from_user.id
    partner_id = await get_partner_id(user_id)
    
    # Check sunflowers
    if bet_amount > 0:
        balance = await get_sunflower_balance(user_id)
        if balance['total'] < bet_amount:
            await callback.answer(
                f"You don't have enough sunflowers! Need {bet_amount}, have {balance['total']}",
                show_alert=True
            )
            return
    
    # Game names
    game_names = {
        'tictactoe': 'Tic Tac Toe',
        'wordchain_easy': 'Word Chain (Easy)',
        'wordchain_hard': 'Word Chain (Hard)',
        'hangman': 'Hangman'
    }
    
    # Send invitation to partner
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Accept", callback_data=f"game_accept:{game_type}:{bet_amount}:{user_id}")
    builder.button(text="❌ Decline", callback_data=f"game_decline:{user_id}")
    builder.adjust(2)
    
    bet_text = f"with {bet_amount} 🌻 bet" if bet_amount > 0 else "with no bet"
    
    await callback.bot.send_message(
        partner_id,
        f"🎮 Your partner wants to play {game_names[game_type]} {bet_text}!",
        reply_markup=builder.as_markup()
    )
    
    await callback.message.edit_text(f"Waiting for partner to accept {game_names[game_type]}...")
    await callback.answer()


@router.callback_query(F.data.startswith("game_accept:"))
async def game_accept_callback(callback: CallbackQuery):
    """Handle game invitation acceptance"""
    parts = callback.data.split(":")
    game_type = parts[1]
    bet_amount = int(parts[2])
    inviter_id = int(parts[3])
    
    accepter_id = callback.from_user.id
    partner_id = await get_partner_id(accepter_id)
    
    if partner_id != inviter_id:
        await callback.answer("You're no longer in chat with this user.", show_alert=True)
        return
    
    # Check sunflowers
    if bet_amount > 0:
        balance = await get_sunflower_balance(accepter_id)
        if balance['total'] < bet_amount:
            await callback.answer(
                f"You don't have enough sunflowers! Need {bet_amount}",
                show_alert=True
            )
            return
    
    # Create game
    chat_id = await get_chat_id(accepter_id)
    
    # Initialize game state
    if game_type == 'tictactoe':
        initial_state = create_tictactoe_state()
    elif game_type.startswith('wordchain'):
        difficulty = 'easy' if game_type == 'wordchain_easy' else 'hard'
        initial_state = create_wordchain_state(difficulty)
    elif game_type == 'hangman':
        initial_state = create_hangman_state()
    
    game_id = await create_game(chat_id, game_type, inviter_id, accepter_id, bet_amount, initial_state)
    
    await callback.message.edit_text("✅ Game accepted! Starting...")
    
    # Start game
    if game_type == 'tictactoe':
        await start_tictactoe(callback.bot, game_id, inviter_id, accepter_id)
    elif game_type.startswith('wordchain'):
        await start_wordchain(callback.bot, inviter_id, accepter_id, initial_state)
    elif game_type == 'hangman':
        await start_hangman(callback.bot, inviter_id, accepter_id, initial_state)
    
    await callback.answer()


@router.callback_query(F.data.startswith("game_decline:"))
async def game_decline_callback(callback: CallbackQuery):
    """Handle game decline"""
    inviter_id = int(callback.data.split(":")[1])
    
    await callback.message.edit_text("❌ You declined the game.")
    await callback.bot.send_message(inviter_id, "Your partner declined the game.")
    await callback.answer()


# ============ TIC TAC TOE ============
async def start_tictactoe(bot, game_id: int, player1_id: int, player2_id: int):
    """Start tic tac toe game"""
    board_markup = create_tictactoe_keyboard(game_id, [''] * 9)
    
    await bot.send_message(
        player1_id,
        "🎯 Tic Tac Toe started! You are X.\nYour turn!",
        reply_markup=board_markup
    )
    await bot.send_message(
        player2_id,
        "🎯 Tic Tac Toe started! You are O.\nWaiting...",
        reply_markup=board_markup
    )


def create_tictactoe_keyboard(game_id: int, board: list):
    """Create tic tac toe inline keyboard"""
    builder = InlineKeyboardBuilder()
    
    for i in range(9):
        text = board[i] if board[i] else str(i+1)
        builder.button(text=text, callback_data=f"ttt:{game_id}:{i}")
    
    builder.adjust(3)
    return builder.as_markup()


@router.callback_query(F.data.startswith("ttt:"))
async def tictactoe_move_callback(callback: CallbackQuery):
    """Handle tic tac toe move"""
    from db.games import get_game_by_id
    
    parts = callback.data.split(":")
    game_id = int(parts[1])
    position = int(parts[2])
    
    user_id = callback.from_user.id
    
    game = await get_game_by_id(game_id)
    
    if not game or game['winner_id'] is not None:
        await callback.answer("Game is over!", show_alert=True)
        return
    
    if user_id != game['current_turn']:
        await callback.answer("Not your turn!", show_alert=True)
        return
    
    # Determine symbol
    symbol = 'X' if user_id == game['player1_id'] else 'O'
    
    # Make move
    success, winner = make_tictactoe_move(game['state'], position, symbol)
    
    if not success:
        await callback.answer("Position taken!", show_alert=True)
        return
    
    # Update state
    next_turn = get_next_player(user_id, game['player1_id'], game['player2_id'])
    await update_game_state(game_id, game['state'], next_turn)
    
    board_markup = create_tictactoe_keyboard(game_id, game['state']['board'])
    
    if winner:
        # Game over
        if winner == 'draw':
            await end_game(game_id, None)
            await callback.bot.send_message(game['player1_id'], "🎯 Draw!")
            await callback.bot.send_message(game['player2_id'], "🎯 Draw!")
        else:
            winner_id = game['player1_id'] if winner == 'X' else game['player2_id']
            loser_id = game['player2_id'] if winner == 'X' else game['player1_id']
            
            await end_game(game_id, winner_id)
            await award_game_winnings(winner_id, loser_id, game['bet_amount'])
            
            total_pot = game['bet_amount'] * 2 + settings.GAME_BASE_REWARD
            await callback.bot.send_message(winner_id, f"🎉 You won! +{total_pot} 🌻")
            await callback.bot.send_message(loser_id, f"😔 You lost. -{game['bet_amount']} 🌻")
        
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        # Continue
        await callback.message.edit_reply_markup(reply_markup=board_markup)
    
    await callback.answer()


# ============ WORD CHAIN ============
async def start_wordchain(bot, player1_id: int, player2_id: int, state: dict):
    """Start word chain game"""
    first_word = state['words'][0]
    last_letter = first_word[-1]
    
    await bot.send_message(
        player1_id,
        f"📝 Word Chain started!\nFirst word: {first_word}\n\nYour turn! Send a word starting with '{last_letter}'"
    )
    await bot.send_message(
        player2_id,
        f"📝 Word Chain started!\nFirst word: {first_word}\n\nWaiting for partner..."
    )


# ============ HANGMAN ============
async def start_hangman(bot, player1_id: int, player2_id: int, state: dict):
    """Start hangman game"""
    from services.game_engine import format_hangman_word
    
    display = format_hangman_word(state)
    
    msg_text = f"🔤 Hangman started!\n\nWord: {display}\nWrong guesses: 0/{state['max_wrong']}\n\nGuess a letter!"
    
    await bot.send_message(player1_id, msg_text)
    await bot.send_message(player2_id, msg_text)


# ============ GAME REWARDS ============
async def award_game_winnings(winner_id: int, loser_id: int, bet_amount: int):
    """Award game winnings"""
    total_pot = bet_amount * 2 + settings.GAME_BASE_REWARD
    
    # Award winner
    await add_sunflowers(winner_id, total_pot, 'game')
    
    # Deduct from loser
    if bet_amount > 0:
        await deduct_sunflowers_smart(loser_id, bet_amount)
