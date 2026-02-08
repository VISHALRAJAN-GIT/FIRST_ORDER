# AI Job Agent 🚀

An intelligent agent that enhances your resume based on a job description and automates the application process.

## Features
- **AI Resume Tailoring**: Uses Google Gemini to rewrite your resume for specific job roles.
- **Smart PDF Generation**: Automatically generates a professional PDF version of your enhanced resume.
- **Browser Automation**: Navigates to job application links and fills out forms using Playwright.
- **Premium UI**: Modern glassmorphism design with React and Framer Motion.

## Project Structure
- `/backend`: FastAPI service handling AI and automation.
- `/frontend`: Vite + React application for the user interface.

## Prerequisites
- Python 3.9+
- Node.js 18+
- Gemini API Key (stored in `backend/.env`)

## Getting Started

### 1. Setup
Run the setup script to install all dependencies:
```bash
./setup.bat
```

### 2. Run the Backend
```bash
cd backend
python -m app.main
```

### 3. Run the Frontend
```bash
cd frontend
npm run dev
```

The application will be available at `http://localhost:5173`.
Automated API will be available at `http://localhost:8000`.

## Architecture
- **Backend Framework**: FastAPI
- **AI Model**: Google Gemini 1.5 Flash
- **Browser Automation**: Playwright
- **Frontend**: React + Tailwind (Glassmorphism CSS)
- **Animations**: Framer Motion
