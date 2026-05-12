# German Rental Contract Review Tool

A web application for analyzing German rental contracts using AI. The tool extracts key information, identifies potential issues, and provides basic contract analysis.

## Features

- **PDF and Text File Support**: Upload German rental contracts in PDF or text format
- **German Language Processing**: Uses spaCy with German language model for text analysis
- **Key Term Detection**: Identifies important rental contract terms (Miete, Kaution, Kündigung, etc.)
- **Named Entity Recognition**: Extracts names, dates, and other entities from contracts
- **Basic Issue Detection**: Flags potential problems like excessive security deposits
- **Docker Containerization**: Easy deployment on any machine

## Architecture

- **Backend**: Python FastAPI with spaCy for German NLP processing
- **Frontend**: Simple HTML/JavaScript interface for file upload and results display
- **Containerization**: Docker and Docker Compose for easy deployment

## Quick Start

### Prerequisites

- Docker and Docker Compose installed on your system

### Running the Application

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd contract_review_tool
   ```

2. Start the application using Docker Compose:

   ```bash
   docker-compose up --build
   ```

3. Open your browser and navigate to:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5001

### Usage

1. Open the frontend at http://localhost:3000
2. Click "Choose File" and select a German rental contract (PDF or text file)
3. Click "Analyze Contract" to process the document
4. View the analysis results including:
   - Basic statistics (word count, sentences)
   - Key rental terms found
   - Named entities extracted
   - Potential issues detected

## Development

### Backend Development

The backend is built with FastAPI and uses spaCy for German text processing. To run locally:

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 5001
```

### Frontend Development

The frontend is a simple static HTML/JavaScript application. To run locally:

```bash
cd frontend
# Serve with any static file server, e.g., using Python:
python -m http.server 8000
```

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /analyze` - Analyze uploaded contract file
  - Accepts: `multipart/form-data` with `file` field
  - Returns: JSON with analysis results

## Technologies Used

- **Backend**: Python, FastAPI, spaCy (German model), PyPDF2
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Containerization**: Docker, Docker Compose
- **NLP**: spaCy with de_core_news_sm model

## Future Enhancements

- Advanced contract clause analysis
- Legal compliance checking
- Multi-language support
- User authentication and contract history
- Integration with legal databases
