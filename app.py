services:
  - type: web
    name: ymn-routing
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    plan: free
