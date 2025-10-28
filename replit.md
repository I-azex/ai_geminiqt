# AI Accounting Assistant (ИИ-бухгалтер)

## Overview
This is an AI-powered accounting assistant application that helps process invoices, answer accounting questions, and analyze financial documents using Google's Gemini AI. The application supports multiple transactions per document and maintains a complete history of all processed files.

**Current Status:** ✅ Fully functional and deployed on Replit
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

### ⚠️ **Anomaly Detection (NEW)**
Intelligent detection of unusual or problematic transactions:
- Outlier detection for unusual amounts using ML (IsolationForest)
- Missing required fields (INN, counterparty, amount)
- Automatic flagging with detailed reasons
- Visual warnings in UI for anomalous transactions
- Anomaly count displayed in file history

### 💬 **Document Q&A (NEW)**
Ask questions about uploaded documents:
- Optional question field when uploading files
- AI analyzes the document and answers your question
- Answers are saved with the file for future reference
- Examples: "What is the total amount?", "Who is the supplier?"

### 📋 **Complete History Tracking**
- All uploaded files are saved to SQLite database
- View all previously processed documents
- Access transaction details at any time
- No need to re-upload files

### 💬 **AI Chatbot**
Ask accounting questions and get expert answers from Gemini AI

### 🎨 **Modern Purple UI Design**
Beautiful purple/violet gradient theme with modern glassmorphism effect:
- Smooth gradients and transitions
- Responsive design across all pages
- Consistent color scheme throughout the application
- Modern card-based layout with subtle shadows

### 📊 **Real-Time Statistics**
Live statistics widget displaying:
- Online users count (session-based tracking)
- Files being processed count
- Auto-updates every 5 seconds
- Visible on main page

### 📝 **Markdown Text Formatting**
AI responses support rich markdown formatting:
- Bold, italic, lists, code blocks
- Properly rendered using marked.js library
- Safe rendering with XSS protection
- Applied to chat responses and document Q&A answers

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
│   ├── stats_tracker.py        # Real-time statistics tracking
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
- `/api/stats` - GET endpoint for real-time statistics (JSON)

## Database Schema

### Tables

**uploaded_files**
- id (PRIMARY KEY)
- filename (TEXT)
- upload_date (TIMESTAMP)
- file_type (TEXT)
- status (TEXT)
- user_question (TEXT) - Optional question about the document
- ai_answer (TEXT) - AI's answer to the question

**transactions**
- id (PRIMARY KEY)
- file_id (FOREIGN KEY)
- inn (TEXT)
- counterparty (TEXT)
- amount (TEXT)
- date (TEXT)
- purpose (TEXT)
- account (TEXT)
- is_anomaly (INTEGER) - 1 if anomaly detected, 0 otherwise
- anomaly_reasons (TEXT) - JSON array of reasons for anomaly
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

### October 28, 2025 - Modern UI Redesign & Real-Time Statistics
- **🎨 Modern Purple UI Design:**
  - Completely redesigned interface with purple/violet gradient theme
  - Applied modern glassmorphism effect across all pages
  - Smooth CSS transitions and animations
  - Responsive card-based layout with subtle shadows
  - Consistent color scheme throughout the application
- **📊 Real-Time Statistics Widget:**
  - Created `stats_tracker.py` module for tracking user activity and file processing
  - Session-based online user tracking with automatic cleanup (5 minutes)
  - File processing count tracking
  - Added `/api/stats` JSON endpoint for statistics
  - Statistics widget auto-refreshes every 5 seconds
- **📝 Markdown Text Formatting:**
  - Integrated marked.js library for rendering markdown in AI responses
  - Applied to chat answers and document Q&A sections
  - Safe rendering with proper escaping to prevent XSS attacks
  - Support for bold, italic, lists, code blocks, and more
- **🔒 Security Improvements:**
  - Fixed critical XSS vulnerability in FILE_DETAIL_TEMPLATE
  - Replaced unsafe template literal injection with |tojson filter
  - Applied JSON-based escaping for all AI-generated content
  - Consistent security approach across all templates

### October 28, 2025 - Anomaly Detection & Document Q&A
- **⚠️ Anomaly Detection:**
  - Implemented ML-based outlier detection using IsolationForest
  - Detects missing required fields (INN, counterparty, amount)
  - Detects unusual amounts compared to other transactions
  - Visual highlighting of anomalous transactions with orange borders
  - Detailed anomaly reasons displayed in UI
  - Anomaly count shown in file metadata
- **💬 Document Q&A:**
  - Added optional question field to upload form
  - Users can ask questions about the document during upload
  - Gemini API processes document and question together
  - Answers saved to database and displayed in file detail view
  - Graceful error handling for API failures
- **Database Updates:**
  - Added `user_question` and `ai_answer` fields to uploaded_files table
  - Added `is_anomaly` and `anomaly_reasons` fields to transactions table
  - Idempotent migrations for existing databases
- **UI Improvements:**
  - Anomaly badge on transactions
  - Color-coded anomaly warnings (orange)
  - Q&A section in file detail view
  - Better visual hierarchy for anomalous data

### October 28, 2025 - Replit Deployment Setup
- ✅ Installed Python 3.11 and all required dependencies
- ✅ Installed system package: tesseract (for OCR)
- ✅ Configured GEMINI_API_KEY secret
- ✅ Created .gitignore for Python project
- ✅ Set up workflow to run Flask server on port 5000
- ✅ Configured deployment with Gunicorn for production (autoscale mode)
- ✅ Verified web interface is working correctly
- ✅ Database automatically initialized

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
- Advanced filtering and search in history (filter by anomalies)
- Transaction editing capabilities
- Bulk document processing
- Dashboard with statistics and charts
- Tunable anomaly detection thresholds
- Integration tests for anomaly detection and Q&A flows
