from langchain_core.tools import tool

# Hardcoded data for demonstration
ORDERS = {
    "ORD-001": {"customer_id": "CUST-A", "amount": 59.99, "status": "delivered", "items": ["Wireless Mouse"]},
    "ORD-002": {"customer_id": "CUST-B", "amount": 350.00, "status": "shipped", "items": ["Ergonomic Chair"]}
}
CUSTOMERS = {
    "CUST-A": {"name": "Alice Smith", "email": "alice@example.com", "account_tier": "standard"},
    "CUST-B": {"name": "Bob Jones", "email": "bob@example.com", "account_tier": "premium"}
}

@tool
def lookup_order(order_id: str) -> dict:
    """Looks up specific details about an order including the customer_id and the amount paid."""
    return ORDERS.get(order_id, {"error": "Order not found"})

@tool
def lookup_customer(customer_id: str) -> dict:
    """Retrieves customer details including their email address and tier."""
    return CUSTOMERS.get(customer_id, {"error": "Customer not found"})

@tool
def process_refund(order_id: str, amount: float) -> dict:
    """Processes a refund for a given order ID and literal dollar amount."""
    correct_amount = ORDERS.get(order_id, {}).get("amount", -1)
    
    print("\n" + "*"*60)
    print("💰 EXECUTING REFUND API")
    print(f"Target Order: {order_id}")
    print(f"Amount Fired: ${amount}")
    if amount == correct_amount:
        print(f"Validation: ✅ SUCCESS (Matches actual paid amount ${correct_amount})")
    else:
        print(f"Validation: ❌ DANGER! (Incorrect amount. Actual was ${correct_amount})")
    print("*"*60 + "\n")
    return {"status": "success", "transaction_id": "TXN-999"}

@tool
def send_confirmation_email(to_email: str, order_id: str, refund_amount: float) -> dict:
    """Sends a confirmation email regarding a processed refund."""
    print(f"📧 [EMAIL SENT TO {to_email}] Order {order_id} refunded ${refund_amount}")
    return {"status": "sent"}

demo_tools = [lookup_order, lookup_customer, process_refund, send_confirmation_email]
