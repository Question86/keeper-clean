# MODE: SCRIPT\n\n```python
class BankAccount:
    def __init__(self, balance=0):
        self.balance = balance
    
    def deposit(self, amount):
        self.balance += amount
    
    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
        else: 
            print('Insufficient funds')
        
    def get_balance(self):
        return self.balance
```