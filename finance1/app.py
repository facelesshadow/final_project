import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


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
    """Show portfolio of stocks"""
    if request.method == "GET":
        rows = db.execute("SELECT username from users WHERE id=?", session["user_id"])
        username = rows[0]["username"]
        rows = db.execute("SELECT * from users WHERE username=?", username)
        cash = rows[0]['cash']
        stock_list = db.execute("SELECT DISTINCT symbol from portfolio WHERE username=?", username)
        stocks_total = 0
        final_list = []

        for entry in stock_list:
            symbol = entry["symbol"]

            #calculate the current price of the symbol
            current_price_list = lookup(symbol)
            current_price = current_price_list["price"]

            #calculate the qty of the stocks
            qty = 0 #keeps track of the amount of stocks of that symbol in the portfolio
            dict_list = db.execute("SELECT buy, qty FROM portfolio WHERE username=? AND symbol=?", username, symbol)
            for entry in dict_list:
                if entry["buy"] == 0:
                    qty -= entry["qty"]
                elif entry["buy"] == 1:
                    qty += entry["qty"]

            #calculcate current total money of stock holdings
            total_stock_cash = qty*current_price

            #in order to Calculate grand total in future
            stocks_total += total_stock_cash

            #populate the dict
            local_dict = {"symbol": symbol, "qty": qty, "current_price": current_price, "total_stock_cash": total_stock_cash}

            #append the list of dicts
            if qty == 0:
                continue
            else:
                final_list.append(local_dict)
        grand_total = stocks_total + cash
        return render_template("index.html", final_list=final_list, cash=cash, grand_total=grand_total)
    return apology("TODO")



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        render_template("buy.html")
    elif request.method == "POST":
        #Get username, Symbol and number of shares
        rows = db.execute("SELECT username from users WHERE id=?", session["user_id"])
        username = rows[0]["username"]
        symbol = request.form.get("symbol")
        qty = request.form.get("shares")
        rows = db.execute("SELECT * from users WHERE username=?", username)
        cash = rows[0]['cash']

        #Check if number of shares are valid (non negative integers)
        if (str.isdigit(qty) == False):
            return apology("Invalid Shares, not numbers")
        elif (str.isdecimal(qty) == False):
            return("invalid Shares")
        qty = int(qty)

        result = lookup(symbol)
        if result is None:
            return apology("Symbol Doesn't exist")
        else:
            price = result["price"]
            total = qty*price
            if(total > cash):
                return apology("Not Enough Cash")
            else:
                db.execute("INSERT INTO portfolio(username, buy, symbol, price, qty, total) VALUES (?, ?, ?, ?, ?, ?)", username, 1, symbol, price, qty, total)
                db.execute("UPDATE users SET cash=? WHERE username=?", cash-total, username)
                return redirect("/")
    return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "GET":
        rows = db.execute("SELECT username from users WHERE id=?", session["user_id"])
        username = rows[0]["username"]
        transactions = db.execute("SELECT * from portfolio WHERE username=?", username)
        for entry in transactions:
            if entry["buy"] == 1:
                entry["buy"] = "Buy"
            else:
                entry["buy"] = "Sell"
        return render_template("history.html", transactions=transactions)
    return apology("TODO")




@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # Redirect user to home page
        return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")



@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        render_template("quote.html")

    elif request.method == "POST":
        symbol = request.form.get("symbol")
        result = lookup(symbol)
        if result is None:
            return apology("Symbol Does Not Exist")
        else:
            name = result["name"]
            price = usd(int(result["price"]))
            symbol = result["symbol"]
        return render_template("quoted.html", name=name, price=price, symbol=symbol)
    return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        if not request.form.get("username"):
            return apology("Empty Field")
        elif not request.form.get("password"):
            return apology("Empty Field")
        elif not request.form.get("confirmation"):
            return apology("Empty Field")

        username = request.form.get("username")
        password = request.form.get("password")
        password2 = request.form.get("confirmation")

        if password != password2:
                return apology("Password does not match")

        rows = db.execute("SELECT * from users where username=?", username)
        for row in rows:
            if username == row["username"]:
                return apology("Username already exists")

        password = generate_password_hash(password)

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, password)
        return redirect("/")
    return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        rows = db.execute("SELECT username from users WHERE id=?", session["user_id"])
        username = rows[0]["username"]
        stock_list = db.execute("SELECT DISTINCT symbol from portfolio WHERE username=?", username)
        new_stock_list = []

        for symbol_dict in stock_list:
            symbol = symbol_dict["symbol"]
            initial_qty = 0 #keeps track of the amount of stocks of that symbol in the portfolio
            dict_list = db.execute("SELECT buy, qty FROM portfolio WHERE username=? AND symbol=?", username, symbol)
            for entry in dict_list:
                if entry["buy"] == 0:
                    initial_qty -= entry["qty"]
                elif entry["buy"] == 1:
                    initial_qty += entry["qty"]
            print(f"{symbol} qty is {initial_qty}")
            if initial_qty > 0:
                new_stock_list.append(symbol_dict)
        return render_template("sell.html", stocks=new_stock_list)

    elif request.method == "POST":
        rows = db.execute("SELECT username from users WHERE id=?", session["user_id"])
        username = rows[0]["username"]
        symbol = request.form.get("symbol") #symbol of stock to sell
        qty = int(request.form.get("shares")) #qty given by user to sell
        rows = db.execute("SELECT * from users WHERE username=?", username) #total cash
        cash = rows[0]['cash']
        result = lookup(symbol)
        if qty <= 0:
            return apology("Invalid number of shares")
        if result is None:
            return apology("Symbol Doesn't exist")
        else:
            #check if the enetered amount of stock are enough
            initial_qty = 0 #keeps track of the amount of stocks of that symbol in the portfolio
            dict_list = db.execute("SELECT buy, qty FROM portfolio WHERE username=? AND symbol=?", username, symbol)
            for entry in dict_list:
                if entry["buy"] == 0:
                    initial_qty -= entry["qty"]
                elif entry["buy"] == 1:
                    initial_qty += entry["qty"]
            if initial_qty < qty:
                return apology(f"{symbol} has {initial_qty} stocks")
            else:
                #add a new transaction in portfolio
                current = lookup(symbol)
                current_price = current['price']
                total = current_price*qty
                db.execute("INSERT INTO portfolio (username, buy, symbol, price, qty, total) VALUES (?, ?, ?, ?, ?, ?)", username, 0, symbol, current_price, qty, total)
                new_cash = cash + total
                #update the cash
                db.execute("UPDATE users SET cash=? WHERE username=?", new_cash, username)
    return redirect("/")



@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    if request.method == "GET":
        return render_template("delete.html")
    elif request.method == "POST":
        rows = db.execute("SELECT username from users WHERE id=?", session["user_id"])
        username = rows[0]["username"]
        print(f"username is {username}")
        db.execute("DELETE from users WHERE username=?", username)
        logout()
        return redirect("/")


