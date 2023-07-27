from cs50 import SQL
import datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
import pytz
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, bj_inital, bj_score, bj_save_p_hands, bj_save_d_hands, bj_get_p_hands, bj_get_d_hands, bj_current_deck, bj_hit, bj_clear_hands, bj_save_bet, bj_get_bet, record_game

# Config app
app = Flask(__name__)

# Config session
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Config sql database
db = SQL("sqlite:///game.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    user = db.execute("SELECT username, cash FROM users WHERE id = ?", session["user_id"])
    return render_template("index.html", user=user)


@app.route("/history")
@login_required
def history():
    records = db.execute("SELECT * FROM records JOIN games ON records.game_id = games.id WHERE user_id = ?", session["user_id"])
    return render_template("history.html", records=records)


@app.route("/game")
@login_required
def game():
    # choose game
    return render_template("index.html")


@app.route("/blackjack", methods=["GET", "POST"])
@login_required
def blackjack():

    if request.method == "POST":

        choice = request.form.get("choice")
        game = "blackjack"
        bonus_win = 2
        bonus_blackjack = 3
        bonus_charlie = 5

        if choice == "start":

            # get user's placed bet
            bet = int(request.form.get("finalbet"))
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            if bet > cash[0]["cash"]:
                flash("You don't have enough cash to place this bet")
                return render_template("blackjack-start.html")
            db.execute("UPDATE users SET cash = ? WHERE id = ?", int(cash[0]["cash"]) - bet, session["user_id"])

            # start a new game
            deck = [*range(1,105)]
            player_hand = bj_inital(deck)
            dealer_hand = bj_inital(deck)

            # dealer immediate win
            if bj_score(dealer_hand) == 21:
                flash("🤦‍♂️ 🤦‍♂️ You lose! Dealer gets a blackjack 🤦‍♂️ 🤦‍♂️")
                record_game("lose", bet, game)
                return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, bet=bet)
            
            # player immediate win
            elif bj_score(player_hand) == 21:
                flash("🎉 🎉 You win! You get a blackjack 🎉 🎉")
                record_game("win", bet, game)
                reward = bet * bonus_blackjack
                db.execute("UPDATE users SET cash = ? WHERE id = ?", int(cash[0]["cash"]) + reward, session["user_id"])
                return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, reward=reward)

            # remember player's card            
            bj_save_p_hands(player_hand)
            bj_save_d_hands(dealer_hand)
            bj_save_bet(bet)
            
            # continue game
            return render_template("blackjack-game.html", player_hand=player_hand, dealer_hand=dealer_hand, bet=bet)
        
        if choice == "hit":

            # get current bet
            bet = bj_get_bet()
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

            # get current hands
            player_hand = bj_get_p_hands()
            dealer_hand = bj_get_d_hands()
            deck = bj_current_deck(player_hand, dealer_hand)

            # add one more card to player
            player_hand.append(bj_hit(deck))

            # if player bust
            if bj_score(player_hand) > 21:
                flash("🤦‍♂️ 🤦‍♂️ Bust! You lose! 🤦‍♂️ 🤦‍♂️")
                record_game("lose", bet, game)
                return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, bet=bet)

            # if player charlie
            elif len(player_hand) == 5:
                flash("🐉 🐉 🐉 🐉 🐉 Charlie! You win! 🐉 🐉 🐉 🐉 🐉")
                record_game("win", bet, game)
                reward = bet * bonus_charlie
                db.execute("UPDATE users SET cash = ? WHERE id = ?", int(cash[0]["cash"]) + reward, session["user_id"])
                return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, reward=reward)

            # remember player's card            
            bj_save_p_hands(player_hand)
            bj_save_d_hands(dealer_hand)
            bj_save_bet(bet)

            # continue game
            return render_template("blackjack-game.html", player_hand=player_hand, dealer_hand=dealer_hand, bet=bet)


        if choice == "stand":

            # get current bet
            bet = bj_get_bet()
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

            # get current hands
            player_hand = bj_get_p_hands()
            dealer_hand = bj_get_d_hands()
            deck = bj_current_deck(player_hand, dealer_hand)

            while bj_score(dealer_hand) < 17:
                dealer_hand.append(bj_hit(deck))

            if bj_score(dealer_hand) > 21:
                flash("🎉 🎉 You win! Dealer busts! 🎉 🎉")
                record_game("win", bet, game)
                reward = bet * bonus_win
                db.execute("UPDATE users SET cash = ? WHERE id = ?", int(cash[0]["cash"]) + reward, session["user_id"])
                return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, reward=reward)

            elif len(dealer_hand) == 5:
                flash("🤦‍♂️ 🤦‍♂️ You lose! Dealer gets Charlie! 🤦‍♂️ 🤦‍♂️")
                record_game("lose", bet, game)
                return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, bet=bet)

            elif bj_score(dealer_hand) >= bj_score(player_hand):
                flash("🤦‍♂️ 🤦‍♂️ You lose! Dealer wins! 🤦‍♂️ 🤦‍♂️")
                record_game("lose", bet, game)
                return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, bet=bet)

            else:
                flash("🎉 🎉 You win! Dealer loses! 🎉 🎉")
                record_game("win", bet, game)
                reward = bet * bonus_win
                db.execute("UPDATE users SET cash = ? WHERE id = ?", int(cash[0]["cash"]) + reward, session["user_id"])
                return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, reward=reward)

        if choice == "quit":
            
            # get current bet
            bet = bj_get_bet()
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            
            # get current hands
            player_hand = bj_get_p_hands()
            dealer_hand = bj_get_d_hands()

            flash("🏳 🏳 Surrender! 🏳 🏳")
            bet /= 2
            db.execute("UPDATE users SET cash = ? WHERE id = ?", int(cash[0]["cash"]) + bet, session["user_id"])
            record_game("surrender", bet, game)
            return render_template("blackjack.html", player_hand=player_hand, dealer_hand=dealer_hand, bet=bet)

    else:
        # ensure table drop before new game starts
        bj_clear_hands()
        return render_template("blackjack-start.html")



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirm_pw = request.form.get("confirm_password")
        
        # check username is not empty
        if not username:
            flash("Please enter a username")
            return render_template("register.html")

        # check password is not empty
        elif not password:
            flash("Please enter a password")
            return render_template("register.html")
        
        # check password confirmation is not empty
        elif not confirm_pw:
            flash("Please enter password confirmation")
            return render_template("register.html")
            
        # check username length
        elif len(username) < 4:
            flash("Minimum length of username: 4")
            return render_template("register.html")
        
        # check password length
        elif len(password) < 4:
            flash("Minimun length of password: 4")
            return render_template("register.html")
        
        # check password confirmation
        elif password != confirm_pw:
            flash("Password confirmation does not match")
            return render_template("register.html")
        
        # check username is unique
        db_name = db.execute("SELECT username FROM users WHERE username = ?", username)
        if db_name:
            flash("Username has already been taken")
            return redirect(url_for('register'))
        
        # create user in database
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password, method='pbkdf2', salt_length=16))
        
        # redirect to homepage
        return redirect("/")
    
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    # clear session
    session.clear()
    
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        
        # check username is not empty
        if not username:
            flash("Please enter a username")
            return render_template("login.html")

        # check password is not empty
        elif not password:
            flash("Please enter a password")
            return render_template("login.html")
        
        # check user credential in database
        db_user = db.execute("SELECT id, username, hash FROM users WHERE username = ?", username)

        # check username exist
        if not db_user:
            flash("Invalid username")
            return render_template("login.html")
        
        # check password
        elif not check_password_hash(db_user[0]["hash"], password):
            flash("Invalid password")
            return render_template("login.html")
        
        session["user_id"] = db_user[0]["id"]

        return redirect("/")
    
    return render_template("login.html")


@app.route("/logout")
def logout():

    # clear user session
    session.clear()
    return redirect("/")


@app.route("/change-username", methods=["GET", "POST"])
@login_required
def change_username():

    if request.method == "POST":

        # get form data
        new_username = request.form.get("new_username")

        # get current username
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])

        # check old username is submitted
        if not new_username:
            flash("Please enter your new username")
            return render_template("change-username.html", username=username[0]["username"])
        
        # check username length
        elif len(new_username) < 4:
            flash("Minimum length of username: 4")
            return render_template("change-username.html", username=username[0]["username"])

        # check new username is different
        if new_username == username[0]["username"]:
            flash("New username cannot be same as your current username")
            return render_template("change-username.html", username=username[0]["username"])
        
        # check new username is unqiue
        db_name = db.execute("SELECT username FROM users WHERE username = ?", new_username)
        if db_name:
            flash("Username has already been taken")
            return render_template("change-username.html", username=username[0]["username"])
        
        # update datbase
        db.execute("UPDATE users SET username = ? WHERE id = ?", new_username, session["user_id"])
        
        # display success message
        flash("Successful!")
        return render_template("change-username.html", username=new_username)

    else:
        username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        return render_template("change-username.html", username=username[0]["username"])


@app.route("/reset-password", methods=["GET", "POST"])
@login_required
def reset_password():

    if request.method == "POST":

        # get form data
        old_pw = request.form.get("old_pw")
        new_pw = request.form.get("new_pw")
        confirm_pw = request.form.get("confirm_pw")

        # get user current password hash
        db_pw = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])

        # check old password is submitted
        if not old_pw:
            flash("Please enter your current password")
            return render_template("reset-password.html")
        
        # check new password is submitted
        elif not new_pw:
            flash("Please enter your new password")
            return render_template("reset-password.html")
        
        # check password confirmation is submitted
        elif not confirm_pw:
            flash("Please enter your new password confirmation")
            return render_template("reset-password.html")
        
        # check user typed password with database current password
        elif not check_password_hash(db_pw[0]["hash"], old_pw):
            flash("Incorrect current password")
            return render_template("reset-password.html")
        
        # check password length
        elif len(new_pw) < 4:
            flash("Minimun length of password: 4")
            return render_template("reset-password.html")
        
        # check password confirmation
        elif new_pw != confirm_pw:
            flash("Password confirmation does not match")
            return render_template("reset-password.html")
        
        elif old_pw == new_pw:
            flash("New password cannot be same as your current password")
            return render_template("reset-password.html")
        
        # update database
        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new_pw, method='pbkdf2', salt_length=16), session["user_id"])
        
        # display success message
        flash("Successful!")
        return render_template("reset-password.html")
    
    else:
        return render_template("reset-password.html")

