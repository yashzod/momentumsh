# momentumsh

#Requirements
python 3.9 (won't work for version>3.9)
node.js

#Setup
python -m venv venv
python install -r requirements.txt

#start fast api app
uvicorn views:app --reload
Access UI with index.html
