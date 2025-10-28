# AI Accounting Assistant (ИИ-бухгалтер)

## Overview
This is an AI-powered accounting assistant application that helps process invoices, answer accounting questions, and analyze financial documents using Google's Gemini AI. The application supports multiple transactions per document and maintains a complete history of all processed files.

**Current Status:** ✅ Fully functional with history tracking and multi-transaction support
**Last Updated:** October 28, 2025

## Key Features

### 📄 **Multi-Transaction Document Processing**
Upload invoices and financial documents (PDF, JPG, PNG) to automatically extract **multiple transactions** from a single document:
- Supplier INN (tax ID)
- Counterparty name
- Amount
- Date
- Payment purpose
- Automatic accounting classification (счет)

### 📋 **Complete History Tracking**
- All uploaded files are saved to SQLite database
- View all previously processed documents
- Access transaction details at any time
- No need to re-upload files

### 💬 **AI Chatbot**
Ask accounting questions and get expert answers from Gemini AI

### 🎨 **Loading Animations**
Beautiful loading spinners with informative messages during document processing

## Project Structure
```
├── modules/
│   ├── chatbot_interface.py    # Flask web application with UI
│   ├── document_parser.py      # PDF/image processing with Gemini (multi-transaction)
│   ├── accounting_logic.py     # Transaction classification logic
│   ├── database.py             # SQLite database operations
│   ├── anomaly_detector.py     # ML-based anomaly detection
│   └── reports_generator.py    # Financial report generation
├── data/
│   ├── uploads/                # Uploaded files storage
│   ├── outputs/                # Processing results
│   └── accounting.db           # SQLite database
├── config.py                   # Configuration with environment variables
├── run_app.py                  # Application entry point
└── requirements.txt            # Python dependencies
```

## Technologies
- **Backend:** Python 3.11, Flask
- **AI:** Google Gemini API (gemini-2.5-flash, gemini-1.5-pro)
- **Database:** SQLite3
- **ML:** scikit-learn, pandas
- **Document Processing:** pdfplumber, pytesseract, pypdfium2
- **Deployment:** Gunicorn (production)

## Environment Variables
- `GEMINI_API_KEY` - Google Gemini API key (required)

## Running the Application
The application runs automatically on port 5000:
- **Development:** `python run_app.py`
- **Production:** Uses Gunicorn with autoscaling

## Web Interface

### Pages
- `/` - Main page with upload form and chat interface
- `/history` - View all processed files with transaction counts
- `/file/<id>` - View detailed information about a specific file and all its transactions
- `/upload` - POST endpoint for file upload
- `/chat` - POST endpoint for chatbot

## Database Schema

### Tables

**uploaded_files**
- id (PRIMARY KEY)
- filename (TEXT)
- upload_date (TIMESTAMP)
- file_type (TEXT)
- status (TEXT)

**transactions**
- id (PRIMARY KEY)
- file_id (FOREIGN KEY)
- inn (TEXT)
- counterparty (TEXT)
- amount (TEXT)
- date (TEXT)
- purpose (TEXT)
- account (TEXT)
- created_at (TIMESTAMP)

## Features in Detail

### Multi-Transaction Support
The application can extract multiple transactions from documents containing:
- Multiple invoice lines
- Batch payment lists
- Transaction tables
- Statement of accounts

### History Functionality
- Automatic saving of all uploaded files
- Transaction count display for each file
- Chronological ordering (newest first)
- Quick access to previously processed documents
- No data loss - all results are persisted

### Loading States
- Visual feedback during document processing
- Disabled buttons to prevent double-submission
- Informative loading messages

## Development Notes
- All file uploads are saved to `data/uploads/`
- Processing results are stored in SQLite database
- The app uses Google Gemini API for document analysis and chat responses
- Server binds to 0.0.0.0:5000 for Replit proxy compatibility
- Database is automatically initialized on first run

## Recent Changes

### October 28, 2025 - Major Feature Update
- **Multi-Transaction Support:** Parser now extracts all transactions from a single document
- **History Tracking:** Added SQLite database for persistent storage
- **New Pages:**
  - `/history` - View all processed files
  - `/file/<id>` - View detailed transaction information
- **Improved UI:**
  - Loading animations with spinners
  - Transaction count display
  - Better navigation between pages
  - Responsive transaction display
- **Database Module:** Created `modules/database.py` for all data operations
- **Enhanced Parser:** Updated prompts to extract multiple transactions
- **Better Error Handling:** Improved handling of various response formats from Gemini
- **Security Fix:** Applied `secure_filename()` to prevent path traversal attacks
- **Smart Validation:** Warning messages when zero transactions are successfully processed

### October 28, 2025 - Initial Setup
- Configured GEMINI_API_KEY from secrets
- Added PDF upload functionality with web UI
- Implemented document processing with visual feedback
- Set up deployment configuration with Gunicorn
- Created .gitignore for Python project

## Future Enhancements
- Export transactions to Excel/CSV
- Advanced filtering and search in history
- Transaction editing capabilities
- Bulk document processing
- Dashboard with statistics and charts
