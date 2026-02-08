from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.resume_service import ResumeService
import shutil
import os

router = APIRouter()
resume_service = ResumeService()

@router.post("/enhance")
async def enhance_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...)
):
    # Save the file temporarily
    temp_dir = "temp_resumes"
    processed_dir = "processed_resumes"
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    file_path = f"{temp_dir}/{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process the resume
        enhanced_text, pdf_path = await resume_service.enhance(file_path, job_description)
        
        # Move enhanced pdf to processed folder
        final_pdf_path = f"{processed_dir}/{os.path.basename(pdf_path)}"
        if os.path.exists(pdf_path):
            shutil.move(pdf_path, final_pdf_path)
            
        return {
            "status": "success", 
            "enhanced_text": enhanced_text,
            "pdf_filename": os.path.basename(final_pdf_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup original
        if os.path.exists(file_path):
            os.remove(file_path)

@router.post("/apply")
async def apply_to_job(
    job_url: str = Form(...),
    pdf_filename: str = Form(...),
    personal_info: str = Form(...) # JSON string
):
    try:
        # Validate personal info JSON
        # In a real app we'd use schemas.PersonalInfo.parse_raw(personal_info)
        result = await resume_service.apply_with_playwright(job_url, pdf_filename, personal_info)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
