git clone https://github.com/testerkind/cafe-guest-counter.git

cd cafe-guest-counter

python -m venv venv

source venv/bin/activate      # Linux/Mac
# или venv\Scripts\activate    # Windows

pip install -r requirements.txt

python app.py

# Открыть http://127.0.0.1:5000
