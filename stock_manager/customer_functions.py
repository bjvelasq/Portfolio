# file name: customer_functions.py

from .stock import Stock  # Import the Stock class for stock interactions
from couchbase.exceptions import DocumentNotFoundException
from datetime import datetime
import traceback

# Deposit funds into a customer's account
def deposit_funds(user_id, amount, user_collection, portfolio_collection):
    """Deposit funds to user's balance and update the portfolio."""
    try:
        # Retrieve the user's current balance from the User collection
        result = user_collection.get(f"user_{user_id}")
        user_data = result.content_as[dict]
        current_balance = user_data.get("balance", 0.0)
        
        # Calculate new balance after deposit
        new_balance = current_balance + amount
        
        # Update the user's balance in the User collection
        user_data["balance"] = new_balance
        user_collection.upsert(f"user_{user_id}", user_data)
        print(f"Deposited {amount} to user {user_id}. New balance: {new_balance}")
        
        # Retrieve the user's portfolio
        portfolio_result = portfolio_collection.get(f"portfolio_{user_id}")
        portfolio_data = portfolio_result.content_as[dict]
        
        # Update the available funds in the portfolio
        portfolio_data["availableFunds"] = new_balance
        portfolio_collection.upsert(f"portfolio_{user_id}", portfolio_data)
        print(f"Updated portfolio for user {user_id} with new available funds: {new_balance}")

    except Exception as e:
        print(f"Error depositing funds for user {user_id}: {e}")


def withdraw_funds(user_id, amount, user_collection, portfolio_collection):
    """Withdraw funds from the user's balance and update the portfolio."""
    try:
        # Retrieve the user's current balance from the User collection
        result = user_collection.get(f"user_{user_id}")
        user_data = result.content_as[dict]
        current_balance = user_data.get("balance", 0.0)
        
        # Check if there are sufficient funds to withdraw
        if current_balance >= amount:
            # Calculate new balance after withdrawal
            new_balance = current_balance - amount
            
            # Update the user's balance in the User collection
            user_data["balance"] = new_balance
            user_collection.upsert(f"user_{user_id}", user_data)
            print(f"Withdrew {amount} from user {user_id}. New balance: {new_balance}")
            
            # Retrieve the user's portfolio
            portfolio_result = portfolio_collection.get(f"portfolio_{user_id}")
            portfolio_data = portfolio_result.content_as[dict]
            
            # Update the available funds in the portfolio
            portfolio_data["availableFunds"] = new_balance
            portfolio_collection.upsert(f"portfolio_{user_id}", portfolio_data)
            print(f"Updated portfolio for user {user_id} with new available funds: {new_balance}")

        else:
            print(f"Insufficient funds to withdraw {amount} from user {user_id}")

    except Exception as e:
        print(f"Error withdrawing funds for user {user_id}: {e}")

# Buy stock for a customer
def buy_stock(user_id, stock_code, quantity, user_collection, stock_collection, portfolio_collection):
    try:
        # Retrieve user, stock, and portfolio documents
        user_result = user_collection.get(f"user_{user_id}")
        stock_result = stock_collection.get(f"stock_{stock_code}")
        portfolio_result = portfolio_collection.get(f"portfolio_{user_id}")

        user_data = user_result.content_as[dict]
        stock_data = stock_result.content_as[dict]
        portfolio_data = portfolio_result.content_as[dict]

        # Retrieve balance from the user collection
        user_balance = user_data.get('balance', 0.0)  # Assuming balance is stored in user_data

        # Calculate total price and check available funds
        total_price = stock_data['price'] * quantity
        if user_balance >= total_price:
            # Deduct funds from user balance
            user_balance -= total_price

            # Update the user's balance in the user collection
            user_data['balance'] = user_balance
            user_collection.upsert(f"user_{user_id}", user_data)  # Update the user document with new balance

            # Update the portfolio stocks
            portfolio_data['userStocks'] = portfolio_data.get('userStocks', {})
            portfolio_data['userStocks'][stock_code] = portfolio_data['userStocks'].get(stock_code, 0) + quantity

            # Ensure stock quantity is available
            if stock_data['quantity_available'] >= quantity:
                stock_data['quantity_available'] -= quantity
            else:
                print(f"Not enough stock available to fulfill order for {stock_code}.")
                return

            # Update Couchbase documents for portfolio and stock
            portfolio_collection.upsert(f"portfolio_{user_id}", portfolio_data)
            stock_collection.upsert(f"stock_{stock_code}", stock_data)

            print(f"Bought {quantity} shares of {stock_code} for user {user_id}. New balance: ${user_balance:.2f}")
            print(f"Stock {stock_code} quantity updated to {stock_data['quantity_available']}")
        else:
            print("Insufficient funds to buy stock.")

    except DocumentNotFoundException as e:
        print(f"Document not found: {e}")
    except Exception as e:
        print(f"Error buying stock: {e}")

def sell_stock(user_id, stock_code, quantity, user_collection, stock_collection, portfolio_collection):
    try:
        # Retrieve user and stock documents
        portfolio_result = portfolio_collection.get(f"portfolio_{user_id}")
        stock_result = stock_collection.get(f"stock_{stock_code}")
        user_result = user_collection.get(f"user_{user_id}")  # Get user data to update balance

        portfolio_data = portfolio_result.content_as[dict]
        stock_data = stock_result.content_as[dict]
        user_data = user_result.content_as[dict]  # Get the user data

        # Check if user has enough stock to sell
        if portfolio_data['userStocks'].get(stock_code, 0) >= quantity:
            # Update portfolio stocks and available funds
            portfolio_data['userStocks'][stock_code] -= quantity
            portfolio_data['availableFunds'] += stock_data['price'] * quantity

            # Update the user's balance with the funds from selling
            user_data['balance'] += stock_data['price'] * quantity  # Add the sale proceeds to the user's balance

            # Update stock quantity available
            stock_data['quantity_available'] += quantity

            # Update Couchbase documents
            portfolio_collection.upsert(f"portfolio_{user_id}", portfolio_data)
            stock_collection.upsert(f"stock_{stock_code}", stock_data)
            user_collection.upsert(f"user_{user_id}", user_data)  # Don't forget to update the user's balance

            print(f"Sold {quantity} shares of {stock_code} for user {user_id}. New available funds: ${portfolio_data['availableFunds']:.2f}")
            print(f"User's new balance: ${user_data['balance']:.2f}")  # Print the updated balance for verification
        else:
            print(f"User does not have enough shares of {stock_code} to sell.")

    except Exception as e:
        print(f"Error selling stock: {e}")

# View Portfolio
def view_portfolio(user_id, portfolio_collection):
    try:
        # Retrieve the portfolio document for the user
        portfolio_result = portfolio_collection.get(f"portfolio_{user_id}")
        portfolio_data = portfolio_result.content_as[dict]

        # Display available funds
        available_funds = portfolio_data.get("availableFunds", 0.0)
        print(f"\nPortfolio for user {user_id}:")
        print(f"Available Funds: ${available_funds:.2f}")

        # Display owned stocks
        user_stocks = portfolio_data.get("userStocks", {})
        if user_stocks:
            print("\nStocks owned:")
            for stock_code, quantity in user_stocks.items():
                print(f"- {stock_code}: {quantity} shares")
        else:
            print("\nNo stocks owned currently.")

    except DocumentNotFoundException:
        print(f"Portfolio for user ID '{user_id}' not found.")
    except Exception as e:
        print(f"Error retrieving portfolio: {e}")