import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'premium-saas-jwt-super-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///smartlift_saas.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email settings
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL') or "smartlift.notifications@gmail.com"
    SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD') or "sdda ergt iwen hnxj"
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'