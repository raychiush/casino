from cs50 import SQL
import datetime
import requests
from flask import redirect, render_template, session, flash
from functools import wraps
import random

# Config sql database
db = SQL("sqlite:///game.db")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def record_game(result, bet, game):
    t = datetime.datetime.now()
    game_id = db.execute("SELECT id FROM games WHERE game = ?", game)
    db.execute("INSERT INTO records (user_id, game_id, result, bet, year, month, day, hour, minute, second) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        session["user_id"], game_id[0]["id"], result, bet, t.year, t.month, t.day, t.hour, t.minute, t.second)
    
        
def bj_inital(deck):
    hand = []
    for i in range(2):
        random.shuffle(deck)
        hand.append(deck.pop())
    return hand
        

def bj_score(hand):
    score = 0
    hand.sort()
    for card in hand:
        if card in range(1, 5) or card in range(53, 57): score += 2
        elif card in range(5, 9) or card in range(57, 61): score += 3
        elif card in range(9, 13) or card in range(61, 65): score += 4
        elif card in range(13, 17) or card in range(65, 69): score += 5
        elif card in range(17, 21) or card in range(69, 73): score += 6
        elif card in range(21, 25) or card in range(73, 77): score += 7
        elif card in range(25, 29) or card in range(77, 81): score += 8
        elif card in range(29, 33) or card in range(81, 85): score += 9
        elif card in range(33, 49) or card in range(85, 101): score += 10

    for card in hand:
        if card in range(49, 53) or card in range(101, 105) and score >= 11: score += 1
        elif card in range(49, 53) or card in range(101, 105) and score < 11: score += 11

    return score


def bj_current_deck(player_hand, dealer_hand):
    deck = [*range(1, 105)]
    for card in player_hand:
        deck.remove(card)
    for card in dealer_hand:
        deck.remove(card)
    return deck


def bj_hit(deck):
    random.shuffle(deck)
    return deck.pop()
    

def bj_save_p_hands(player_hand):
    db.execute("INSERT INTO p_hands (user_id) VALUES (?)", session["user_id"])
    for i in range(len(player_hand)):
        db.execute("UPDATE p_hands SET ? = ? WHERE user_id = ?", f"p_hand{i+1}", player_hand[i], session["user_id"])
    return


def bj_save_d_hands(dealer_hand):
    db.execute("INSERT INTO d_hands (user_id) VALUES (?)", session["user_id"])
    for i in range(len(dealer_hand)):
        db.execute("UPDATE d_hands SET ? = ? WHERE user_id = ?", f"d_hand{i+1}", dealer_hand[i], session["user_id"])
    return


def bj_save_bet(bet):
    db.execute("UPDATE p_hands SET bet = ? WHERE user_id = ?", bet, session["user_id"])


def bj_get_p_hands():
    hands = []
    hand = db.execute("SELECT * FROM p_hands WHERE user_id = ?", session["user_id"])

    for i in range(5):
        if hand[0][f"p_hand{i+1}"]:
            hands.append(int(hand[0][f"p_hand{i+1}"]))

    return hands


def bj_get_d_hands():
    hands = []
    hand = db.execute("SELECT * FROM d_hands WHERE user_id = ?", session["user_id"])

    for i in range(5):
        if hand[0][f"d_hand{i+1}"]:
            hands.append(int(hand[0][f"d_hand{i+1}"]))

    return hands


def bj_get_bet():
    bet = db.execute("SELECT bet FROM p_hands WHERE user_id = ?", session["user_id"])
    return int(bet[0]["bet"])


def bj_clear_hands():
    db.execute("DELETE FROM p_hands WHERE user_id = ?", session["user_id"])
    db.execute("DELETE FROM d_hands WHERE user_id = ?", session["user_id"])