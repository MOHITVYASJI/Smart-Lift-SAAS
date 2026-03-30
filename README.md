# SmartLift SaaS

A B2B SaaS platform for secure lift access management in educational institutions and enterprises.

## Features

- Multi-tenant architecture with strict data isolation
- Facial recognition and QR code authentication
- Real-time access logging and analytics
- Visitor pass management with email notifications
- Emergency event tracking
- Admin dashboard with date-filtered analytics
- CSV export for logs

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables:
   - `SECRET_KEY`: Flask secret key
   - `DATABASE_URL`: Database URI (default: SQLite)
   - `SENDER_EMAIL`: SMTP email
   - `SENDER_PASSWORD`: SMTP password
   - `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
4. Run database migrations: `python app.py` (creates tables)
5. Start the app: `python app.py`

## Production Deployment

- Use a production WSGI server like Gunicorn: `gunicorn -w 4 app:app`
- Use PostgreSQL for the database
- Set up environment variables securely
- Enable HTTPS
- Configure logging to files

## Usage

- SuperAdmin: Login with founder@smartlift.com to manage tenants
- Tenant Admin: Manage users, visitor passes, view logs
- Edge Node: Run `python main.py` for hardware simulation

## Security

- Tenant data isolation
- Secure password hashing
- Session management
- Input validation

## License

Proprietary