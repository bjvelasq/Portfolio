# file name: stock_app.py

from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions
from couchbase.exceptions import CouchbaseException, DocumentNotFoundException
from datetime import timedelta
from .stock_user import User # Import User class
from .stock import Stock  # Import Stock Class
from .customer_functions import deposit_funds, withdraw_funds, buy_stock, sell_stock, view_portfolio
import traceback
import random
import time

# Connection configuration
endpoint = "couchbases://cb.nnq3yiry4lf6y7e2.cloud.couchbase.com"
username = "Admin"  # Username
password = "Password123!"  # Password
bucket_name = "Stocks"  # Stock bucket name
user_bucket_name = "User"  # User bucket name
portfolio_bucket_name = "Portfolios" # Portfolio bucket name
scope_name = "_default"  
collection_name = "_default" 

# Connect options - authentication
auth = PasswordAuthenticator(username, password)
options = ClusterOptions(auth)
options.apply_profile("wan_development")

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

# Scope and collection setup for stocks
stock_scope = stock_bucket.scope(scope_name) if scope_name else stock_bucket.default_scope()
stock_collection = stock_scope.collection(collection_name) if collection_name else stock_bucket.default_collection()

# Scope and collection setup for users
user_scope = user_bucket.scope(scope_name) if scope_name else user_bucket.default_scope()
user_collection = user_scope.collection(collection_name) if collection_name else user_bucket.default_collection()

# Scope and collection setup for portfolios
portfolio_scope = portfolio_bucket.scope(scope_name) if scope_name else portfolio_bucket.default_scope()
portfolio_collection = portfolio_scope.collection(collection_name) if collection_name else portfolio_bucket.default_collection()

# Use user_collection and portfolio_collection for operations on User and Portfolio data.
print("Collection setup completed.")

# Function to retrieve stock info based on stock code and return a Stock object
def get_stock_info(stock_code):
    try:
        return stock_collection.get(f"stock_{stock_code}").content
    except:
        return None
    
def update_stock(stock_code, updated_data):
    try:
        # Fetch the stock document from the database
        stock = stock_collection.get(f"stock_{stock_code}")

        # Check if stock exists
        if not stock:
            raise Exception(f"Stock with code '{stock_code}' not found.")

        # Access the stock data (it should be in 'value')
        stock_data = stock.value

        # Update high and low prices based on the new price
        new_price = updated_data['price']
        if new_price > stock_data.get('high_price', new_price):
            stock_data['high_price'] = new_price
        if new_price < stock_data.get('low_price', new_price):
            stock_data['low_price'] = new_price

        # Update the current price and other stock data
        stock_data.update(updated_data)  # Update the stock data with the new values

        # Save the updated stock back into the database
        stock_collection.upsert(f"stock_{stock_code}", stock_data)

        print(f"Stock '{stock_code}' price updated successfully!")

    except Exception as e:
        print(f"Error updating stock: {str(e)}")
        raise

# Function to add a new stock
def add_stock(stock_code, stock_name, price, high_price, low_price, quantity_available):
    try:
        stock_data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'price': price,
            'high_price': high_price,
            'low_price': low_price,
            'quantity_available': quantity_available 
        }
        # Insert the stock into Couchbase
        stock_collection.upsert(f"stock_{stock_code}", stock_data)
        print(f"Stock '{stock_code}' added successfully!")
    except Exception as e:
        raise Exception(f"Error adding stock: {e}")

# Function to remove a stock
def remove_stock(stock_code):
    try:
        stock_collection.remove(f"stock_{stock_code}")
    except Exception as e:
        raise Exception(f"Error removing stock: {e}")

# Admin menu for managing stock data
def admin_functions():
    while True:
        print("\nAdmin Menu:")
        print("1. Update Stock Information")
        print("2. Add New Stock")
        print("3. Remove Stock")
        print("4. Exit Admin Menu")

        choice = input("Enter your choice: ").strip()
        if choice == '1':
            update_stock()
        elif choice == '2':
            add_stock()
        elif choice == '3':
            remove_stock()
        elif choice == '4':
            print("Exiting Admin Menu.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

def customer_functions():
    print("Customer functions started.")
    while True:
        print("\nCustomer Menu:")
        print("1. View Stock Information")
        print("2. Deposit Funds")
        print("3. Withdraw Funds")
        print("4. Buy Stock")
        print("5. Sell Stock")
        print("6. View Portfolio")
        print("7. Exit")

        choice = input("Enter your choice: ").strip()
        if choice == '1':
            stock_code = input("Enter the stock code you want to search for: ").strip()
            stock = get_stock_info(stock_code)
            if stock:
                stock.display_stock_info()
            else:
                print(f"Stock with code '{stock_code}' not found.")

        elif choice == '2':
            user_id = input("Enter your user ID for deposit: ").strip()
            amount = float(input("Enter amount to deposit: ").strip())
            deposit_funds(user_id, amount, user_collection, portfolio_collection)

        elif choice == '3':
            user_id = input("Enter your user ID for withdrawal: ").strip()
            amount = float(input("Enter amount to withdraw: ").strip())
            withdraw_funds(user_id, amount, user_collection)

        elif choice == '4':
            user_id = input("Enter your user ID for buying stock: ").strip()
            stock_code = input("Enter stock code: ").strip()
            quantity = int(input("Enter quantity to buy: ").strip())
            buy_stock(user_id, stock_code, quantity, user_collection, stock_collection, portfolio_collection)

        elif choice == '5':
            user_id = input("Enter your user ID for selling stock: ").strip()
            stock_code = input("Enter stock code: ").strip()
            quantity = int(input("Enter quantity to sell: ").strip())
            sell_stock(user_id, stock_code, quantity, user_collection, stock_collection, portfolio_collection)

        elif choice == '6':
            user_id = input("Enter your user ID to view your portfolio: ").strip()
            view_portfolio(user_id, portfolio_collection)

        elif choice == '7':
            print("Exiting Customer Menu.")
            break

        else:
            print("Invalid choice. Please enter a valid option.")

def user_role(user):
    print(f"User role detected: {'Admin' if user.is_admin else 'Customer'}")
    # user.display_user_info()  # Display user information
    if user.is_admin:
        print("Welcome, Admin!")
        admin_functions()  # Admin can update stock information
    else:
        print("Welcome, Customer!")
        customer_functions()

# Function to search for a user in the Couchbase User bucket
def find_user(user_id, password):
    try:
        # Retrieve the user data from Couchbase using user_collection
        result = user_collection.get(f"user_{user_id}")  # Get user document by user_id
        user_data = result.content_as[dict]  # Convert the result to a dictionary
        
        if user_data['password'] == password:
            # Instantiate the User object if credentials match
            user = User(
                user_id=user_data['userID'],
                user_email=user_data['email'],
                user_name=user_data['userName'],
                is_admin=user_data['isAdmin'],
                password=user_data['password'],
                user_collection=user_collection,
                portfolio_collection=portfolio_collection
            )
            return user
        else:
            print("Incorrect password.")
            return None
    except DocumentNotFoundException:
        print(f"User with ID '{user_id}' not found.")
        return None
    except Exception as e:
        print(f"Error retrieving user information: {e}")
        return None
    
def find_user_by_username(username):
    """
    Find a user by their username without checking the password.
    """
    try:
        # Retrieve the user data from Couchbase using user_collection
        result = user_collection.get(f"user_{username}")  # Get user document by username
        user_data = result.content_as[dict]  # Convert the result to a dictionary
        
        # Instantiate the User object
        user = User(
            user_id=user_data['userID'],
            user_email=user_data['email'],
            user_name=user_data['userName'],
            is_admin=user_data['isAdmin'],
            password=user_data['password'],
            user_collection=user_collection,
            portfolio_collection=portfolio_collection
        )
        return user
    
    except couchbase.exceptions.DocumentNotFoundException:
        # Handle the case where the document is not found
        print(f"User with username '{username}' not found.")
        return None
    except Exception as e:
        print(f"Error retrieving user information: {e}")
        return None

# Function to create a new user and save to the User bucket
def create_user():
    # Collect user information
    user_id = input("Enter user ID: ")
    user_email = input("Enter user email: ")
    user_name = input("Enter user name: ")
    is_admin = input("Is the user an admin? (yes/no): ").lower() == "yes"
    password = input("Please enter a password: ")

    try:
        # Create the User object
        user = User(
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            is_admin=is_admin,
            password=password,
            user_collection=user_collection,  # Assume `user_collection` is defined
            portfolio_collection=portfolio_collection  # Assume `portfolio_collection` is defined
        )

        # Create the user document in the user collection
        user.create_user()

        # If the user is not an admin, create a portfolio for them
        if not is_admin:
            user.create_portfolio()

        print(f"User {user_name} with ID {user_id} created successfully.")

        return user

    except Exception as e:
        print(f"Error creating user: {e}")

# Function to display the main menu
def main_menu():
    while True:
        print("\nWelcome to the Stock Management Application!")
        print("1. Create a new user.")
        print("2. Login as an existing user.")
        print("3. Exit")

        choice = input("Enter your choice: ").strip()
        if choice == '1':
            create_user()  # Create a new user
        elif choice == '2':
            user_id = input("Enter your user ID: ")  # Ask for user ID
            password = input("Enter password: ")
            user = find_user(user_id, password)  # Search for user in the User bucket

            if user is None:
                print("User not found. Please try again.")
            else:
                print("User found. Proceeding...")
                user_role(user)  # Use the same user object in both admin and customer functions
        elif choice == '3':
            print("Exiting application.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

def fluctuate_stock_prices():
    """
    Fetch all stock IDs and simulate random fluctuations in their prices.
    """
    try:
        # Fetch all stock documents (or stock IDs) from Couchbase using N1QL query
        query = "SELECT META().id FROM `Stocks`"
        result = cluster.query(query)

        # Ensure that the query executes successfully and fetch the rows
        rows = list(result)  # Execute the query and get the rows as a list
        print(f"Query result: {rows}")  # Print rows to check the result
        
        # Loop through each stock ID
        for row in rows:
            stock_id = row['id']
            fluctuate_stock_price(stock_id)
            print(f"Prices fluctuating for stock ID: {stock_id}")
    
    except CouchbaseException as e:
        print(f"Error fetching stock IDs: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def fluctuate_stock_price(stock_id):
    """
    Simulates random fluctuations in a stock's price and updates its record in the database.
    """
    try:
        # Fetch the stock document from Couchbase
        stock_doc = stock_collection.get(stock_id).content_as[dict]

        # Existing values
        current_price = stock_doc.get('price', 0.0)
        high_price = stock_doc.get('high_price', 0.0)
        low_price = stock_doc.get('low_price', 0.0)

        # Simulate fluctuation (+/- 2%)
        fluctuation_percentage = random.uniform(-0.02, 0.02)  # +/- 2% fluctuation
        new_price = current_price * (1 + fluctuation_percentage)

        # Calculate new high/low prices
        stock_doc['price'] = new_price
        stock_doc['high_price'] = max(new_price, high_price)
        stock_doc['low_price'] = min(new_price, low_price)

        # Update the stock document in Couchbase
        stock_collection.upsert(stock_id, stock_doc)

        # Log the new stock prices for debugging
        print(f"Stock ID: {stock_id}, Updated Price: {new_price}, High: {stock_doc['high_price']}, Low: {stock_doc['low_price']}")

    except DocumentNotFoundException:
        print(f"Error: Stock document with ID {stock_id} not found.")
    except CouchbaseException as e:
        print(f"Error updating stock with ID {stock_id}: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    except DocumentNotFoundException:
        print(f"Error: Stock document with ID {stock_id} not found.")
    except CouchbaseException as e:
        print(f"Error updating stock with ID {stock_id}: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def start_fluctuation_task():
    """
    Starts the fluctuation task that updates all stock prices every 60 seconds.
    """
    while True:
        fluctuate_stock_prices()  # Fetch all stock IDs and update their prices
        time.sleep(60)  # Wait 60 seconds before the next fluctuation

# Main function to start the application
if __name__ == "__main__":
    print("Starting application...")
    main_menu()  # Start the application