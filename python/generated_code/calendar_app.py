```python

import tkinter as tk
import datetime

class CalendarApp:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title('Calendar Application')
        self.year, self.month = self.get_current_date()
        self.create_widgets()
    
    def get_current_date(self):
        return datetime.date.today().year, datetime.date.today().month
    
    def create_widgets(self):
        # Add necessary code to create calendar UI using tkinter

if __name__ == '__main__':
    app = CalendarApp()
    app.window.mainloop()
```