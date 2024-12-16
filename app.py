from stock_manager.stock_app import find_user, add_stock, update_stock, remove_stock, get_stock_info, start_fluctuation_task
from stock_manager import stock_app
from stock_manager import customer_functions
from stock_manager.customer_functions import deposit_funds, withdraw_funds, buy_stock, sell_stock, view_portfolio
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions
from couchbase.exceptions import CouchbaseException, DocumentNotFoundException
from datetime import timedelta
from stock_manager import stock_user
from stock_manager.stock_user import User
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
from couchbase.cluster import Cluster, ClusterOptions
from couchbase.auth import PasswordAuthenticator
from flask import jsonify
import sys
import os
import traceback
import uuid
import threading
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'stock_manager'))

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'

# Connection configuration
endpoint = "couchbases://cb.nnq3yiry4lf6y7e2.cloud.couchbase.com"
username = "Admin"  # Username
password = "Password123!"  # Password
bucket_name = "Stocks"  # Stock bucket name
user_bucket_name = "User"  # User bucket name
portfolio_bucket_name = "Portfolios" # Portfolio bucket name
transaction_bucket_name = "TransactionHistory" # Transaction History Bucket name
scope_name = "_default"  
collection_name = "_default" 

# Connect options - authentication
auth = PasswordAuthenticator(username, password)
options = ClusterOptions(auth)
# options.apply_profile("wan_development") # apply_profile deprecated and not needed I believe

try:
    # Get a reference to the Couchbase cluster
    cluster = Cluster(endpoint, options)
    # Wait until the cluster is ready for use
    cluster.wait_until_ready(timedelta(seconds=5))
    print("Connected to Couchbase cluster successfully!")
except Exception as e:
    traceback.print_exc()

# Bucket connection
bucket = cluster.bucket(bucket_name)
user_bucket = cluster.bucket(user_bucket_name)  # Connect to the User bucket
portfolio_bucket = cluster.bucket(portfolio_bucket_name)  # Connect to the Portfolio bucket
stock_bucket = cluster.bucket(bucket_name)  # Connect to the Stock bucket (same bucket as `bucket_name`)
transaction_bucket = cluster.bucket(transaction_bucket_name) # Connect to the transaction history bucket

# Scope and collection setup for stocks
stock_scope = stock_bucket.scope(scope_name) if scope_name else stock_bucket.default_scope()
stock_collection = stock_scope.collection(collection_name) if collection_name else stock_bucket.default_collection()

# Scope and collection setup for users
user_scope = user_bucket.scope(scope_name) if scope_name else user_bucket.default_scope()
user_collection = user_scope.collection(collection_name) if collection_name else user_bucket.default_collection()

# Scope and collection setup for portfolios
portfolio_scope = portfolio_bucket.scope(scope_name) if scope_name else portfolio_bucket.default_scope()
portfolio_collection = portfolio_scope.collection(collection_name) if collection_name else portfolio_bucket.default_collection()

# Scope and collection setup for transaction history
transaction_scope = transaction_bucket.scope(scope_name) if scope_name else transaction_bucket.default_scope()
transaction_collection = transaction_scope.collection(collection_name) if collection_name else transaction_bucket.default_collection()

# Use user_collection and portfolio_collection for operations on User and Portfolio data.
print("Collection setup completed.")

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

# Home page for logged out users
@app.route('/')
def home_logged_out():
    try:

        query = """
            SELECT stock_code, stock_name, price
            FROM `Stocks`
            ORDER BY price DESC
            LIMIT 3
        """

        rows = cluster.query(query)
        

        stocks = [{'symbol': row['stock_code'], 'name': row['stock_name'], 'price': row['price']} for row in rows]


        return render_template('HomePage(LoggedOut).html', stocks=stocks)

    except Exception as e:
        print(f"Error fetching stocks: {e}")
        return render_template('HomePage(LoggedOut).html', stocks=[])

# Home page for logged in users
@app.route('/home_logged_in')
def home_logged_in():
    try:

        query = """
            SELECT stock_code, stock_name, price
            FROM `Stocks`
            ORDER BY price DESC
            LIMIT 3
        """

        rows = cluster.query(query)
        

        stocks = [{'symbol': row['stock_code'], 'name': row['stock_name'], 'price': row['price']} for row in rows]

        # Render the HomePage template with stock data
        return render_template('HomePage(LoggedIn).html', stocks=stocks)

    except Exception as e:
        print(f"Error fetching stocks: {e}")
        return render_template('HomePage(LoggedIn).html', stocks=[])

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = find_user(username, password)  # Retrieves user details and checks password
        
        if user:
            session['user_id'] = user.user_name  # Store only the username in the session
            flash('Logged in successfully', 'success')
            
            # Check if the user is an admin and redirect accordingly
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home_logged_in'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', form=form)

# Sign Up page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        user_name = request.form['name']
        user_email = request.form['email']
        user_username = request.form['username']
        user_password = request.form['password']
        
        is_admin = False  # Set to False by default for normal users

        try:
            # Call the create_user function to create a new user
            user = create_user(user_username, user_email, user_name, is_admin, user_password)
            
            flash("User created successfully! Please log in.", 'success')
            return redirect(url_for('login'))  # Redirect to the login page after successful sign up

        except Exception as e:
            flash(f"Error creating user: {str(e)}", 'error')

    return render_template('SignUpPage.html')

def create_user(user_id, user_email, user_name, is_admin, password):
    try:
        
        user = User(
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            is_admin=is_admin,
            password=password,
            user_collection=user_collection,
            portfolio_collection=portfolio_collection
        )

        # Create the user document in the user collection
        user.create_user()

        # If the user is not an admin, create a portfolio for them
        if not is_admin:
            user.create_portfolio()

        return user

    except Exception as e:
        raise Exception(f"Error creating user: {e}")

def log_transaction(user_id, transaction_type, stock_code=None, amount=None, quantity=None):
    """
    Logs a transaction in the TransactionHistory bucket.
    """
    transaction_data = {
        "transaction_id": str(uuid.uuid4()),  # Generate a unique ID
        "user_id": user_id,
        "transaction_type": transaction_type,
        "stock_code": stock_code,
        "amount": amount,
        "quantity": quantity,
        "timestamp": datetime.utcnow().isoformat() + "Z",  # ISO 8601 format
    }

    try:
        transaction_collection.insert(transaction_data["transaction_id"], transaction_data)
        print(f"Transaction logged: {transaction_data}")
    except Exception as e:
        print(f"Failed to log transaction: {e}")

def run_fluctuation_in_background():
    """
    Runs the fluctuation task in a background thread.
    """
    print("Starting fluctuation task in background...")
    fluctuation_thread = threading.Thread(target=stock_app.start_fluctuation_task)
    fluctuation_thread.daemon = True  # Allow program to exit even if this thread is running
    fluctuation_thread.start()

# Admin Dashboard page
@app.route('/admin_dashboard')
def admin_dashboard():
    # Check if the user is logged in and is an admin
    if 'user_id' not in session:
        flash('You need to log in first', 'error')
        return redirect(url_for('login'))

    # Get the username of the logged-in user from the session
    username = session['user_id']

    # Find the user using the username (no password check needed)
    user = stock_app.find_user_by_username(username)

    if user and user.is_admin:
        return render_template('adminDashboard.html')  # Render admin dashboard
    else:
        flash('Access denied. Admins only.', 'error')
        return redirect(url_for('home_logged_in'))  # Redirect to home page for non-admins

# Admin Portal page
@app.route('/adminportal')
def admin_portal():
    return render_template('AdminDashboard.html')

# Buy/Sell page
@app.route('/buy_sell')
def buy_sell():
    return render_template('BuySellPage.html')

# Contact Us page
@app.route('/contact')
def contact():
    return render_template('ContactUsPage.html')

# Main stock page
@app.route('/stock_page')
def stock_page():
    try:
        # Query to get all stock documents
        query = "SELECT * FROM `Stocks`"
        result = cluster.query(query)

        # Extract stocks data from the query result
        stocks = [row['Stocks'] for row in result]

        if not stocks:
            print("No stocks available.")
    
        return render_template('MainStockPage.html', stocks=stocks)

    # except CouchbaseError as e:
    #    print(f"CouchbaseError: {str(e)}")
     #   return jsonify({'status': 'error', 'message': f"Failed to fetch stock data: {str(e)}"})
    except Exception as e:
        print(f"Exception: {str(e)}")
        return jsonify({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"})
    
# Portfolio page
@app.route('/portfolio')
def portfolio():
    # Ensure user is logged in
    if 'user_id' not in session:
        flash("You need to log in to view your portfolio.")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    try:
        # Fetch user data from the user collection
        user_result = user_collection.get(f"user_{user_id}")
        user_data = user_result.content_as[dict]
        
        # Get the balance from the user data
        balance = user_data.get('balance', 0.0)
        balance = float(balance)  # Convert to float
        
        # Fetch portfolio data from the portfolio collection
        portfolio_result = portfolio_collection.get(f"portfolio_{user_id}")
        portfolio_data = portfolio_result.content_as[dict]
        
        # Get the user's stock ownership from portfolio data
        owned_stocks = portfolio_data.get('userStocks', {})
        
        # Calculate the total stock value
        total_stock_value = 0.0
        stocks_details = []
        for symbol, quantity in owned_stocks.items():
            try:
                # Fetch stock details from Stocks collection
                stock_result = stock_collection.get(f"stock_{symbol}")
                stock_data = stock_result.content_as[dict]
                
                # Calculate total value for this stock
                stock_price = stock_data.get('price', 0.0)
                stock_total_value = quantity * stock_price
                
                # Add stock info to the list
                stock_info = {
                    'symbol': symbol,
                    'name': stock_data.get('stock_name', 'Unknown'),
                    'price': stock_price,
                    'quantity': quantity,
                    'total_value': stock_total_value
                }
                stocks_details.append(stock_info)
                
                # Add to the overall total stock value
                total_stock_value += stock_total_value
                
            except Exception as e:
                print(f"Error fetching stock {symbol}: {str(e)}")

        # Calculate total assets (cash + total stock value)
        total_assets = balance + total_stock_value
        
        # Pass the data to the template
        return render_template('Portfolio.html', user=user_data, balance=balance, owned_stocks=stocks_details, total_assets=total_assets)
    
    except Exception as e:
        flash(f"Error fetching portfolio: {str(e)}")
        return render_template('Portfolio.html', user={}, balance=0.0, owned_stocks=[], total_assets=0.0)

# Handle deposit funds
@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user_id' not in session:
        flash('Please log in to perform this action.', 'error')
        return redirect(url_for('login'))

    # Assume deposit form submission includes amount
    amount = request.form.get('amount')  # Capture deposit amount from form
    try:
        amount = float(amount)  # Convert the amount to a float
        username = session['user_id']  # Retrieve the logged-in user's ID/username
        
        # Your deposit logic (updating user funds, portfolio, etc.)
        success = deposit_funds(username, amount, user_collection, portfolio_collection)
        
        if success:
            # Log the deposit transaction
            log_transaction(username, "deposit", amount=amount, quantity=None)

            flash('Deposit successful!', 'success')
        else:
            flash('Deposit failed. Please try again.', 'error')
    except ValueError:
        flash('Invalid amount. Please enter a number.', 'error')
    
    return redirect(url_for('home_logged_in'))

# Transaction History page
@app.route('/transaction_history')
def transaction_history():
    try:
        user_id = session.get('user_id')  # Assuming user ID is stored in session
        # Corrected query
        query = f"""
            SELECT * 
            FROM `TransactionHistory`
            WHERE user_id = '{user_id}'
            ORDER BY timestamp DESC
        """
        
        result = cluster.query(query)
        transactions = list(result)

        # Process and print transactions for debugging
        if transactions:
            # Accessing the 'TransactionHistory' key in the result
            processed_transactions = []
            for transaction in transactions:
                # Extracting the transaction data from the nested dictionary
                transaction_data = transaction['TransactionHistory']
                processed_transactions.append(transaction_data)

            print(f"Transactions Retrieved: {processed_transactions}")
        else:
            print("No transactions found.")

        # Pass the processed transactions to the HTML template
        return render_template('TransactionHistory.html', transactions=processed_transactions)
    
    except Exception as e:
        print(f"Error retrieving transaction history: {e}")
        flash("Error retrieving transaction history", "error")
        return redirect(url_for('home_logged_in'))

@app.route('/logout')
def logout():
    session.clear()  # Clear user session
    flash("You have been logged out.")
    return redirect(url_for('home_logged_out'))

# Stock Page
@app.route('/stock/<stock_symbol>', methods=['GET'])
def stock(stock_symbol):
    try:
        # Query to get the stock details for the given symbol, including available quantity
        query = """
            SELECT stock_code, stock_name, price, quantity_available
            FROM `Stocks`
            WHERE stock_code = $stock_symbol
        """
        # Execute the query
        rows = cluster.query(query, stock_symbol=stock_symbol)

        # Process the query result
        stock = None
        for row in rows:
            stock = {
                'symbol': row['stock_code'],
                'name': row['stock_name'],
                'price': row['price'],
                'quantity_available': row['quantity_available'],  # Add available quantity
            }

        if stock is None:
            raise Exception("Stock not found")

        # Render the StockPage template with the stock details
        return render_template('StockPage.html', stock=stock)

    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return render_template('StockPage.html', stock=None)

    except Exception as e:
        print(f"Error fetching stock details: {e}")
        return redirect(url_for('home_logged_in'))  # Redirect back to homepage or handle error appropriately

# Buy Stock Route
@app.route('/buy_stock', methods=['POST'])
def buy_stock_route():
    try:
        user_id = session.get('user_id')  # Assuming user ID is stored in session
        stock_symbol = request.form['stock_symbol']
        quantity = int(request.form['quantity'])

        # Prepend 'stock_' to the stock symbol to match the document naming convention
        stock_document_key = f"stock_{stock_symbol}"

        # Check if the stock document exists
        try:
            stock_doc = stock_collection.get(stock_document_key)
            stock_price = stock_doc.content_as[dict]['price']  # Retrieve the price from the stock document
        except DocumentNotFoundException:
            print(f"Stock {stock_symbol} not found. Creating a new stock document.")
            stock_document = {
                "stock_code": stock_symbol,
                "stock_name": "Unknown",
                "price": 0.0,
                "quantity_available": 0
            }
            # Create the stock document with a placeholder price
            stock_collection.upsert(stock_document_key, stock_document)
            stock_price = 0.0  # Placeholder for stock price until real price is available

        # Calculate the total amount based on stock price and quantity
        total_amount = stock_price * quantity

        # Process the stock purchase (update stock, user portfolio, etc.)
        buy_stock(user_id, stock_symbol, quantity, user_collection, stock_collection, portfolio_collection)

        # Log the transaction with the correct amount (calculated as stock price * quantity)
        log_transaction(user_id, 'buy', stock_symbol, amount=total_amount, quantity=quantity)  # Use calculated total_amount

        return redirect(url_for('stock_page', stock_symbol=stock_symbol))

    except Exception as e:
        print(f"Error processing buy stock request: {e}")
        return redirect(url_for('home_logged_in'))

# Sell Stock Route
@app.route('/sell_stock', methods=['POST'])
def sell_stock_route():
    try:
        user_id = session.get('user_id')  # Assuming user ID is stored in session
        stock_symbol = request.form['stock_symbol']
        quantity = int(request.form['quantity'])

        # Prepend 'stock_' to the stock symbol to match the document naming convention
        stock_document_key = f"stock_{stock_symbol}"

        # Check if the stock document exists
        try:
            stock_doc = stock_collection.get(stock_document_key)
            stock_price = stock_doc.content_as[dict]['price']  # Retrieve the price from the stock document
        except DocumentNotFoundException:
            print(f"Stock {stock_symbol} not found. Cannot process sell.")
            flash('Stock not found. Please check the stock symbol.', 'error')
            return redirect(url_for('home_logged_in'))

        # Calculate the total revenue based on stock price and quantity
        total_revenue = stock_price * quantity

        # Process the stock sale (update stock, user portfolio, etc.)
        sell_stock(user_id, stock_symbol, quantity, user_collection, stock_collection, portfolio_collection)

        # Log the sell transaction with the correct amount (calculated as stock price * quantity)
        log_transaction(user_id, "sell", stock_symbol, amount=total_revenue, quantity=quantity)

        return redirect(url_for('stock_page', stock_symbol=stock_symbol))

    except Exception as e:
        print(f"Error processing sell stock request: {e}")
        return redirect(url_for('home_logged_in'))
    
# Route to handle adding a new stock
@app.route('/add-stock', methods=['POST'])
def add_new_stock():
    try:
        # Extract form data
        stock_data = {
            'stock_name': request.form['stock_name'],
            'stock_code': request.form['stock_code'],
            'price': float(request.form['price']),
            'high_price': float(request.form['high_price']),
            'low_price': float(request.form['low_price']),
            'quantity_available': float(request.form['quantity_available']),
        }

        # Add stock using the stock_app function
        stock_app.add_stock(
            stock_code=stock_data['stock_code'],
            stock_name=stock_data['stock_name'],
            price=stock_data['price'],
            high_price=stock_data['high_price'],
            low_price=stock_data['low_price'],
            quantity_available=stock_data['quantity_available']
        )
        return redirect('/admin_dashboard')  # Redirect after successful addition
    except KeyError as e:
        return jsonify({'status': 'error', 'message': f'Missing field: {e}'})
    except ValueError as e:
        return jsonify({'status': 'error', 'message': 'Invalid input type'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Route to handle editing a stock
@app.route('/edit-stock', methods=['POST'])
def edit_stock():
    try:
        stock_code = request.form['stock_code']
        updated_data = {
            'stock_name': request.form['stock_name'],
            'price': float(request.form['price']),
        }

        # Call the edit_stock function
        stock_app.update_stock(stock_code, updated_data)
        return redirect('/admin_dashboard')  # Redirect after successful editing

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Route to handle removing a stock
@app.route('/remove-stock', methods=['POST'])
def remove_stock():
    try:
        stock_code = request.form['stock_code']

        # Call the remove_stock function
        stock_app.remove_stock(stock_code)
        return redirect('/admin_dashboard')  # Redirect after successful removal

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    run_fluctuation_in_background()
    app.run(debug=True)