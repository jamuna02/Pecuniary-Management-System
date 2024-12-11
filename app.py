from flask import Flask, render_template, request, jsonify, json, url_for, flash, session, redirect
from flask_sqlalchemy import SQLAlchemy
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import  or_ ,  extract
from datetime import datetime, timedelta


from collections import defaultdict
from functools import wraps

app = Flask(__name__)

app.secret_key = 'your_secret_key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost/pms'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Users(db.Model):
    __tablename__ = 'users'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(30), nullable=False)

    

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    party_name = db.Column(db.String(255), nullable=False)
    bill_number = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    type_ = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid_received = db.Column(db.Numeric(10, 2), nullable=False)
    balance = db.Column(db.Numeric(10, 2))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'party_name': self.party_name,
            'bill_number': self.bill_number,
            'date': self.date.strftime('%Y-%m-%d'),  # Formatting date to a string
            'type': self.type_,
            'category': self.category,
            'total_amount': self.total_amount,
            'amount_paid_received': self.amount_paid_received,
            'balance': self.balance
        }
    

@app.route('/')
def home():
    return render_template('index.html')

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']

        if Users.query.filter_by(email=email).first():
            error = 'Email already exists'
            return render_template('index.html', error1=error)
        else:
            new_user = Users(username=name, email=email, mobile=mobile, password=password)
            db.session.add(new_user)
            db.session.commit()
            session['user_id'] = new_user.id  # Store user ID in session

        return render_template('dashboard.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Users.query.filter_by(email=email, password=password).first()

        if user:
            session['user_id'] = user.id  # Store user ID in session
            return redirect(url_for('dashboard'))

        else:
            error = 'Incorrect username or password'
            return render_template('index.html', error=error)
    return render_template('index.html')

@app.route('/transactions', methods=['POST'])
def transactions():
    try:
        # Print form data to debug
        print(request.form)
        
        # Retrieve form data
        party_name = request.form.get('party_name')
        bill_number = request.form.get('bill_number')
        date = request.form.get('date')
        trans_type = request.form.get('type')
        category = request.form.get('category')
        total_amount = float(request.form.get('total_amount'))
        amount_paid_received = float(request.form.get('amount_paid_received'))
        balance = float(total_amount - amount_paid_received)

        # Convert user_id from session to UUID
        user_id = session.get('user_id')

        # Create a new transaction record
        new_transaction = Transaction(
            user_id=user_id,  # Ensure this is a UUID
            party_name=party_name,
            bill_number=bill_number,
            date=date,
            type_=trans_type,  # Use 'trans_type' to avoid conflict with reserved keywords
            category=category,
            total_amount=total_amount,
            amount_paid_received=amount_paid_received,
            balance=balance
        )

        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction successfully added!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))


@app.route('/expenses', methods=['POST'])
def expenses():
    try:
        # Retrieve form data
        party_name = "-"
        bill_number ="-"
        date = request.form['date1']
        trans_type = "Expense"
        category = request.form['category1']
        total_amount = float(request.form['total_amount1'])
        amount_paid_received = float(request.form['amount_paid_received1'])
        balance = float(total_amount - amount_paid_received)

        # Convert user_id from session to UUID
        user_id = session.get('user_id')
        
        # Create a new transaction record
        new_transaction = Transaction(
            user_id=user_id,  # Ensure this is a UUID
            party_name=party_name,
            bill_number=bill_number,
            date=date,
            type_=trans_type,  # Use 'trans_type' to avoid conflict with reserved keywords
            category=category,
            total_amount=total_amount,
            amount_paid_received=amount_paid_received,
            balance=balance
        )        
        try:
            db.session.add(new_transaction)
            db.session.commit()
            flash('Transaction successfully added!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')       
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('dashboard'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:  # Replace with your session check
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('home', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    user = Users.query.filter_by(id=user_id).first()
    username = user.username if user else "User"  # Default to "User" if not found

    transactions = Transaction.query.filter_by(type_='Credit', user_id=user_id).all()
    total_credit = sum(transaction.total_amount for transaction in transactions)
    total_credited_amount = sum(transaction.amount_paid_received for transaction in transactions)
    total_receivable = sum(transaction.balance for transaction in transactions)

    Transactions = Transaction.query.filter_by(type_='Debit', user_id=user_id).all()
    total_debit = sum(Trans.total_amount for Trans in Transactions)
    total_debited_amount = sum(Trans.amount_paid_received for Trans in Transactions)
    total_payable = sum(Trans.balance for Trans in Transactions)

    Transactions = Transaction.query.filter_by(type_='Expense', user_id=user_id).all()
    total_expense_paid = sum(Transac.amount_paid_received for Transac in Transactions)
    need_to_pay=sum(Transac.balance for Transac in Transactions)
    total_expense=sum(Transac.total_amount for Transac in Transactions)

    cash_outflow=total_expense_paid+total_debited_amount 
    payables=total_payable+need_to_pay

    
    d_parties = (
        Transaction.query
        .filter_by(user_id=user_id, type_='Debit')
        .with_entities(Transaction.party_name)
        .distinct()
        .all()
    )
    # Extracting the party names from the results
    d_parties = [party.party_name for party in d_parties]
    
    c_parties = (
        Transaction.query
        .filter_by(user_id=user_id, type_='Credit')
        .with_entities(Transaction.party_name)
        .distinct()
        .all()
    )
    # Extracting the party names from the results
    c_parties = [party.party_name for party in c_parties]

    
    return render_template('dashboard.html', 
        username=username,
        total_credit= total_credit, 
        total_credited_amount=total_credited_amount, 
        total_receivable=total_receivable, 
        total_debit =total_debit, 
        total_debited_amount=total_debited_amount, 
        total_payable=total_payable,
        total_expense_paid =total_expense_paid,
        need_to_pay = need_to_pay,
        total_expense=total_expense,
        cash_outflow=cash_outflow,
        payables=payables,
        d_parties=json.dumps(d_parties),  # Convert to JSON string
        c_parties=json.dumps(c_parties)
    )


@app.route('/credit')
def credit():
    user_id = session.get('user_id')
    transactions = Transaction.query.filter_by(type_='Credit', user_id=user_id).all()

    transaction_list = sorted(
    [
        {
            'id': transaction.id,
            'party_name': transaction.party_name,
            'date': transaction.date.strftime('%Y-%m-%d'),
            'bill_number': transaction.bill_number,
            'type': transaction.type_,
            'category': transaction.category,
            'total_amount': transaction.total_amount,
            'amount_paid_received': transaction.amount_paid_received,
            'balance': transaction.balance
        }
        for transaction in transactions
    ],
    key=lambda x: x['date'],  # Sorting by date
    reverse=True  # Descending order
    )

    # Data for chart
    chart_data = {
        'dates': [transaction['date'] for transaction in transaction_list],
        'amount_received': [transaction['amount_paid_received'] for transaction in transaction_list],
        'receivables': [transaction['balance'] for transaction in transaction_list]
    }
    
    
    return jsonify({'transactions': transaction_list, 'chart_data': chart_data })


@app.route('/debit')
def debit():
    user_id = session.get('user_id')
    transactions = Transaction.query.filter_by(type_='Debit', user_id=user_id).all()

    transaction_list = sorted(
    [
        {
            'id': transaction.id,
            'party_name': transaction.party_name,
            'date': transaction.date.strftime('%Y-%m-%d'),
            'bill_number': transaction.bill_number,
            'type': transaction.type_,
            'category': transaction.category,
            'total_amount': transaction.total_amount,
            'amount_paid_received': transaction.amount_paid_received,
            'balance': transaction.balance
        }
        for transaction in transactions
    ],
    key=lambda x: x['date'],  # Sorting by date
    reverse=True  # Descending order
    )
    
    chart_data = {
        'dates': [transaction['date'] for transaction in transaction_list],
        'amount_paid': [transaction['amount_paid_received'] for transaction in transaction_list],
        'payables': [transaction['balance'] for transaction in transaction_list]
    }
    
    return jsonify({'transactions': transaction_list, 'chart_data': chart_data})


@app.route('/expense')
def expense():
    user_id = session.get('user_id')
    transactions = Transaction.query.filter_by(type_='Expense', user_id=user_id).all()

    transaction_list =sorted([
        {
            'id': transaction.id,  # Include the ID for the edit/delete actions
            'date': transaction.date.strftime('%Y-%m-%d'),
            'category': transaction.category,
            'total_amount': float(transaction.total_amount),  # Convert to float
            'amount_paid_received': float(transaction.amount_paid_received),  # Convert to float
            'balance': float(transaction.balance)  # Convert to float
        }
        for transaction in transactions
    ],
    key=lambda x: x['date'],  # Sorting by date
    reverse=True  # Descending orde
    )

    category_totals = defaultdict(float)
    for transaction in transactions:
        category_totals[transaction.category] += float(transaction.amount_paid_received)  # Convert to float

    chart_data = {
        'categories': list(category_totals.keys()),
        'totals': list(category_totals.values())
    }

    return jsonify({'transactions': transaction_list, 'chart_data': chart_data})

@app.route('/search_parties', methods=['GET'])
def search_parties():
    user_id = session.get('user_id')
    
    parties = sorted(
        Transaction.query
        .filter(
            Transaction.user_id == user_id,
            or_(Transaction.type_ == 'Debit', Transaction.type_ == 'Credit')
        )
        .with_entities(Transaction.party_name)
        .distinct()
        .all()
    )
    parties = [party.party_name for party in parties]
    return jsonify({'parties': parties})    

@app.route('/search_by_week', methods=['POST','GET'])
def search_by_week():
    user_id = session.get('user_id')
    selected_week = request.form.get('dateInput')  # Expecting the week selection (like '2024-W35')
    party_name = request.form.get('spartyname') 

    try:
        year, week = selected_week.split('-W')
        year = int(year)
        week = int(week)
    except ValueError:
        return "Invalid week format", 400

    # Get the start and end date of the selected week
    start_of_week = datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w")
    end_of_week = start_of_week + timedelta(days=6)

    # Query for transactions within the week
    if party_name == 'All':
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.party_name != "-",
            Transaction.date >= start_of_week,
            Transaction.date <= end_of_week
        ).all()
    else:
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.party_name == party_name,
            Transaction.date >= start_of_week,
            Transaction.date <= end_of_week
        ).all()
    return prepare_transaction(transactions)


@app.route('/search_by_month', methods=['POST','GET'])
def search_by_month():
    user_id = session.get('user_id')
    selected_month = request.form.get('dateInput')  # Expecting the month selection (like '2024-09')
    party_name = request.form.get('spartyname')

    # Validate and parse the selected month
    try:
        year, month = selected_month.split('-')
        year = int(year)
        month = int(month)
    except ValueError:
        return "Invalid month format", 400

    # Get the start and end date of the selected month
    start_of_month = datetime(year, month, 1)
    if month == 12:
        end_of_month = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = datetime(year, month + 1, 1) - timedelta(days=1)

    # Query for transactions within the month
    if party_name == 'All':
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.party_name != "-",
            Transaction.date >= start_of_month,
            Transaction.date <= end_of_month
        ).all()
    else:        
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.party_name == party_name,
            Transaction.date >= start_of_month,
            Transaction.date <= end_of_month
        ).all()

    return prepare_transaction(transactions)


@app.route('/search_by_year', methods=['POST','GET'])
def search_by_year():
    user_id = session.get('user_id')
    selected_year = request.form.get('dateInput')  # Expecting year selection (e.g., '2024')
    party_name = request.form.get('spartyname')
    
    try:
        year = int(selected_year)
    except ValueError:
        return "Invalid year format", 400

    # Query for transactions within the selected year
    if party_name == 'All':
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.party_name != "-",
            extract('year', Transaction.date) == year
        ).all()
    else:
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.party_name == party_name,
            extract('year', Transaction.date) == year
        ).all()

    return prepare_transaction(transactions)


def prepare_transaction(transactions):
    # Convert transactions to dictionaries
    transaction_list = sorted(
        [
            {
                'id': transaction.id,
                'party_name': transaction.party_name,
                'date': transaction.date.strftime('%Y-%m-%d'),
                'bill_number': transaction.bill_number,
                'type': transaction.type_,
                'category': transaction.category,
                'total_amount': transaction.total_amount,
                'amount_paid_received': transaction.amount_paid_received,
                'balance': transaction.balance
            }
            for transaction in transactions
        ],
        key=lambda x: x['date'],
        reverse=True
    )

    # Calculate the totals for the summary cards
    total_amt = sum(Trans['total_amount'] for Trans in transaction_list)
    total_pay_receive = sum(Trans['amount_paid_received'] for Trans in transaction_list)
    total_paid_received = sum(Trans['balance'] for Trans in transaction_list)

    # Prepare chart data
    chart_data = {
        'dates': [transaction['date'] for transaction in transaction_list],
        'amount_received': [transaction['amount_paid_received'] for transaction in transaction_list],
        'receivables': [transaction['balance'] for transaction in transaction_list]
    }
    
    transaction_types = set(transaction['type'] for transaction in transaction_list)
    print(transaction_types)

    if 'Debit' in transaction_types and 'Credit' in transaction_types:
        transaction_type = 'both'
    elif 'Credit' not in transaction_types:
        transaction_type = 'Debit'
    elif 'Debit' not in transaction_types:
        transaction_type = 'Credit'
    else:
        transaction_type = None  # Handle case where no transactions exist
        

    # Return the JSON response with transactions and summary data
    return jsonify({
        'transactions': transaction_list, 
        'chart_data': chart_data, 
        'total_amt': total_amt, 
        'pay_receive': total_pay_receive, 
        'paid_received': total_paid_received,
        'transaction_type': transaction_type
    })

    
@app.route('/delete_transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    
    if transaction:
        db.session.delete(transaction)
        db.session.commit()
        return '', 204  # Return No Content status on successful deletion
    else:
        return jsonify({'error': 'Transaction not found'}), 404  



@app.route('/update_transaction/<int:id>', methods=['POST'])
def update_transaction(id):
    data = request.json
    transaction = Transaction.query.get(id)
    if transaction:
        transaction.date = data.get('date')
        new_amount = data.get('amount', 0)
        transaction.amount_paid_received += new_amount
        transaction.balance = transaction.total_amount - transaction.amount_paid_received
        db.session.commit()
        return '', 204
    else:
        return jsonify({'error': 'Transaction not found'}), 404


@app.route('/logout')
def logout():
    session.clear()  # Clear the session to log the user out
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))  # Redirect to the home page


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
