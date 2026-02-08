@echo off
echo Setting up AI Job Agent...

cd backend
echo Installing backend dependencies...
pip install -r requirements.txt
playwright install chromium

cd ../frontend
echo Installing frontend dependencies...
npm install

echo Setup complete! 
echo To run the backend: cd backend && python -m app.main
echo To run the frontend: cd frontend && npm run dev
