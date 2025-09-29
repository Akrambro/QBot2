## Quotex connection setup

Prereqs:
- Python 3.10–3.12 installed

Setup (Windows PowerShell):
```
cd C:\Users\Lenovo\Documents\Bot2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configure environment:
```
copy .env.example .env
# edit .env to add QX_EMAIL and QX_PASSWORD
```

Run connection check:
```
python connect.py
```

If successful, you'll see your account balance printed.


