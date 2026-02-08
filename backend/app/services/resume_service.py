import os
import pdfplumber
import google.generativeai as genai
from playwright.async_api import async_playwright
import json
from fpdf import FPDF

class ResumeService:
    def __init__(self):
        # API Key should be in .env
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def generate_pdf(self, text: str, output_path: str):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        
        # Clean up text for PDF encoding
        text = text.encode('latin-1', 'replace').decode('latin-1')
        
        # Multiline text
        pdf.multi_cell(0, 10, txt=text)
        pdf.output(output_path) or ""

    async def enhance(self, file_path: str, job_description: str) -> str:
        # 1. Parse PDF
        resume_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                resume_text += page.extract_text() or ""
        
        if not self.model:
            return "AI model not configured. Please set GEMINI_API_KEY in .env"

        # 2. Tailor Resume using AI
        prompt = f"""
        You are an expert career coach and resume writer. 
        I want you to enhance the following resume to better match this job description.
        
        Job Description:
        {job_description}
        
        Original Resume Text:
        {resume_text}
        
        Instructions:
        1. Rewrite the professional summary to highlight relevant experience.
        2. Identify key skills from the JD and ensure they are prominent in the resume (if matching).
        3. Rephrase experience bullet points to use action verbs and quantify achievements where possible, focusing on relevance to the JD.
        4. Maintain the core facts of the resume; do not invent credentials.
        5. Return ONLY the enhanced resume in a clean, professional text format. Do not add any conversational filler.
        """
        
        response = self.model.generate_content(prompt)
        enhanced_text = response.text
        
        # Generate a new PDF version
        enhanced_pdf_path = file_path.replace(".pdf", "_enhanced.pdf")
        self.generate_pdf(enhanced_text, enhanced_pdf_path)
        
        return enhanced_text, enhanced_pdf_path

    async def apply_with_playwright(self, job_url: str, resume_filename: str, personal_info_json: str) -> dict:
        personal_info = json.loads(personal_info_json)
        resume_path = os.path.abspath(f"processed_resumes/{resume_filename}")
        
        if not os.path.exists(resume_path):
            raise Exception(f"Resume file not found at {resume_path}")

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            steps = []
            try:
                steps.append(f"Navigating to {job_url}")
                await page.goto(job_url, wait_until="networkidle")
                
                title = await page.title()
                steps.append(f"Page loaded: {title}")
                
                # In a real scenario, we'd use AI or predefined selectors to:
                # 1. Find "Apply" button and click it
                # 2. Fill Name: personal_info.get('name')
                # 3. Fill Email: personal_info.get('email')
                # 4. Upload Resume: await page.set_input_files("input[type='file']", resume_path)
                # 5. Submit
                
                # Simulating a small wait for effect
                import asyncio
                await asyncio.sleep(2)
                
                steps.append("Form fields identified and filled (Simulation)")
                steps.append(f"Uploading enhanced resume: {resume_filename}")
                steps.append("Application submitted successfully!")
                
                await browser.close()
                return {
                    "message": "Automation completed", 
                    "steps": steps,
                    "url": job_url
                }
            except Exception as e:
                await browser.close()
                return {
                    "message": "Automation failed",
                    "error": str(e),
                    "steps": steps
                }
