# SwiftCart

SwiftCart is a full-stack e-commerce web application built using Flask and SQLite. It provides core online shopping features including user authentication with OTP verification, product browsing, cart management, order placement, and email notifications.

## Features

- User registration with email OTP verification
- Secure login with hashed passwords
- Product catalog with categories and search functionality
- Order placement and order history tracking
- Email notifications for OTP verification and order confirmation
- RESTful API architecture
- Lightweight SQLite database

## Tech Stack

- Backend: Flask (Python)
- Database: SQLite
- Frontend: HTML, CSS, JavaScript
- Email Service: SMTP (Gmail)
- Version Control: Git and GitHub

## Project Structure
```
SwiftCart/
│
├── app.py
├── swiftcart.db
├── templates/
│   └── index.html
├── .gitignore
└── README.md
```

## Setup Instructions

1. Clone the repository

git clone https://github.com/aman-coder03/SwiftCart.git
cd SwiftCart

2. Create a virtual environment

python -m venv venv
venv\Scripts\activate   # On Windows

3. Install dependencies

pip install flask flask-cors python-dotenv

4. Configure environment variables

Create a .env file in the root directory and add:

EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password

5. Run the application

python app.py

The server will start at:
http://localhost:5000

## API Endpoints

Authentication
- POST /api/send-otp — Send OTP for registration
- POST /api/register — Register new user
- POST /api/login — User login

User
- PUT /api/profile — Update user profile

Products
- GET /api/products — Get all products (with filters)
- GET /api/categories — Get product categories

Orders
- POST /api/orders — Place a new order
- GET /api/orders/<user_id> — Get user orders

## Deployment

- Frontend can be deployed using Netlify
- Backend should be deployed on platforms like Render or Railway
- Environment variables must be configured on the deployment platform
- SQLite is suitable for development; consider PostgreSQL for production

## Security Notes

- Do not commit .env or database files to version control
- Always use environment variables for sensitive credentials
- Passwords are stored using SHA-256 hashing

## Future Improvements

- Replace SQLite with PostgreSQL
- Add payment gateway integration
- Implement JWT-based authentication
- Improve UI/UX
- Add admin dashboard

## License

This project is for educational purposes and does not include a commercial license.
