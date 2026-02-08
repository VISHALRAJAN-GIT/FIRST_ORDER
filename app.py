from flask import Flask, render_template, request, jsonify, session, make_response
import os
from dotenv import load_dotenv
from backend.core.session import LearningSession
from backend.api.perplexity import PerplexityClient
import backend.utils.database as db
from backend.utils.quiz_generator import QuizGenerator
import json
from pypdf import PdfReader
import docx
import io
from backend.utils.mock_test import MockTestGenerator

load_dotenv()

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Store sessions in memory
sessions = {}
quiz_gen = QuizGenerator()
perplexity_client = PerplexityClient()
mock_test_gen = MockTestGenerator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start-topic', methods=['POST'])
def start_topic():
    data = request.json
    topic = data.get('topic')
    persona = data.get('persona', 'General')
    difficulty = data.get('difficulty', 'Intermediate')
    
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400
    
    session_id = request.cookies.get('session_id', os.urandom(16).hex())
    learning_session = LearningSession(persona=persona, difficulty=difficulty)
    
    try:
        roadmap = learning_session.start_new_topic(topic)
        sessions[session_id] = learning_session
        
        steps = [
            {
                'number': step['number'],
                'title': step['title'],
                'details': step['details']
            }
            for step in roadmap.steps
        ]
        
        # Save to database
        roadmap_data = {'topic': topic, 'steps': steps, 'persona': persona, 'difficulty': difficulty}
        topic_id = db.save_topic(topic, roadmap_data, len(steps))
        
        response = jsonify({
            'success': True,
            'topic': topic,
            'topic_id': topic_id,
            'steps': steps,
            'currentStep': 0
        })
        response.set_cookie('session_id', session_id)
        response.set_cookie('topic_id', str(topic_id))
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-guide', methods=['POST'])
def get_guide():
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    try:
        guide = learning_session.get_detailed_guide_for_step()
        return jsonify({
            'success': True,
            'guide': guide
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/next-step', methods=['POST'])
def next_step():
    session_id = request.cookies.get('session_id')
    topic_id = request.cookies.get('topic_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    step = learning_session.next_step()
    
    # Update progress in database
    if topic_id:
        db.update_topic_progress(int(topic_id), learning_session.current_step_index)
    
    if step:
        return jsonify({
            'success': True,
            'step': {
                'number': step['number'],
                'title': step['title'],
                'details': step['details']
            },
            'currentStepIndex': learning_session.current_step_index
        })
    else:
        return jsonify({
            'success': True,
            'completed': True,
            'message': 'You have completed the roadmap!'
        })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with persona awareness"""
    data = request.json
    message = data.get('message')
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    current_step = learning_session.get_current_step()
    
    try:
        persona_styles = {
            "General": "helpful and clear",
            "Scientist": "academic, precise, and highly technical",
            "ELI5": "extremely simple, using analogies that a 5-year-old would understand",
            "Socratic": "inquisitive, answering with questions that guide the user to discover the answer themselves"
        }
        style = persona_styles.get(learning_session.persona, "helpful")
        
        # Build context-aware prompt
        context = f"""You are a {learning_session.persona} learning assistant. Your teaching style is {style}.
The user is currently learning about:
Topic: {learning_session.roadmap.topic}
Difficulty: {learning_session.difficulty}
Current Step: {current_step['title']}

User question: {message}

Provide a clear, helpful answer in your assigned style ({style}) that relates to their current learning step."""
        
        messages = [{"role": "user", "content": context}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content']
        
        # Save to database
        if topic_id:
            db.save_chat_message(int(topic_id), learning_session.current_step_index, 'user', message)
            db.save_chat_message(int(topic_id), learning_session.current_step_index, 'assistant', ai_response)
        
        return jsonify({
            'success': True,
            'response': ai_response
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    """Generate a quiz for the current step"""
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    current_step = learning_session.get_current_step()
    
    try:
        step_details = '\n'.join(current_step['details']) if current_step['details'] else current_step['title']
        questions = quiz_gen.generate_quiz(
            learning_session.roadmap.topic,
            current_step['title'],
            step_details
        )
        
        return jsonify({
            'success': True,
            'questions': questions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-quiz', methods=['POST'])
def submit_quiz():
    """Submit quiz answers and get score"""
    data = request.json
    answers = data.get('answers', {})
    questions = data.get('questions', [])
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    # Calculate score
    correct = 0
    results = []
    
    for i, question in enumerate(questions):
        user_answer = answers.get(str(i))
        is_correct = quiz_gen.check_answer(question, user_answer) if user_answer else False
        
        if is_correct:
            correct += 1
        
        results.append({
            'question_number': i + 1,
            'correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': question['correct']
        })
    
    # Save to database
    if topic_id:
        db.save_quiz_result(int(topic_id), learning_session.current_step_index, correct, len(questions))
    
    return jsonify({
        'success': True,
        'score': correct,
        'total': len(questions),
        'percentage': round((correct / len(questions)) * 100) if questions else 0,
        'results': results
    })

@app.route('/api/save-note', methods=['POST'])
def save_note():
    """Save a note for the current step"""
    data = request.json
    content = data.get('content')
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    if topic_id:
        db.save_note(int(topic_id), learning_session.current_step_index, content)
    
    return jsonify({'success': True})

@app.route('/api/get-note', methods=['GET'])
def get_note():
    """Get note for current step"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    if topic_id:
        note = db.get_note(int(topic_id), learning_session.current_step_index)
        return jsonify({'success': True, 'note': note})
    
    return jsonify({'success': True, 'note': None})

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """Get all topics"""
    topics = db.get_all_topics()
    return jsonify({'success': True, 'topics': topics})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get learning statistics"""
    topics = db.get_all_topics()
    total_topics = len(topics)
    completed_topics = len([t for t in topics if t['completed']])
    
    # Calculate total steps across all topics
    total_steps = sum([t['total_steps'] for t in topics])
    current_steps = sum([t['current_step'] + 1 for t in topics]) # +1 because current_step is 0-indexed
    
    return jsonify({
        'success': True,
        'totalTopics': total_topics,
        'completedTopics': completed_topics,
        'progress': round((current_steps / total_steps) * 100) if total_steps > 0 else 0
    })

@app.route('/api/export', methods=['GET'])
def export_handbook():
    """Export the current learning session as a Markdown handbook"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return "No active session found.", 400
    
    learning_session = sessions[session_id]
    topic_data = db.get_topic(int(topic_id))
    
    if not topic_data:
        return "Topic not found.", 404
    
    md_content = f"# Learning Handbook: {topic_data['name']}\n"
    md_content += f"**Persona:** {learning_session.persona} | **Difficulty:** {learning_session.difficulty}\n\n"
    md_content += "## Roadmap\n"
    for i, step in enumerate(topic_data['roadmap_data']['steps']):
        md_content += f"### Step {i+1}: {step['title']}\n"
        for detail in step['details']:
            md_content += f"- {detail}\n"
        
        # Add Note
        note = db.get_note(int(topic_id), i)
        if note:
            md_content += f"\n#### My Notes\n> {note}\n"
        
        # Add Chat History
        chat_history = db.get_chat_history(int(topic_id), i)
        if chat_history:
            md_content += f"\n#### Chat History\n"
            for msg in chat_history:
                md_content += f"**{msg['role'].capitalize()}:** {msg['message']}\n\n"
        
        md_content += "\n---\n"
    
    response = make_response(md_content)
    response.headers["Content-Disposition"] = f"attachment; filename={topic_data['name'].replace(' ', '_')}_Handook.md"
    response.headers["Content-Type"] = "text/markdown"
    return response

@app.route('/api/chat-history', methods=['GET'])
def get_chat_history():
    """Get chat history for current step"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    if topic_id:
        history = db.get_chat_history(int(topic_id), learning_session.current_step_index)
        return jsonify({'success': True, 'history': history})
    
    return jsonify({'success': True, 'history': []})

@app.route('/api/get-resources', methods=['POST'])
def get_resources():
    """Fetch related learning resources for the current step"""
    data = request.json
    topic = data.get('topic')
    step_title = data.get('step')
    
    if not topic or not step_title:
        return jsonify({'error': 'Topic and step title are required'}), 400
    
    try:
        prompt = f"""Find 3 highly relevant learning resources (articles, videos, or courses) for someone learning about "{step_title}" in the context of "{topic}".
        Return only a JSON list of objects, each with 'title', 'type' (Article, Video, or Course), and 'url'.
        No other text."""
        
        messages = [{"role": "user", "content": prompt}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content']
        
        # Extract JSON from response if there's any markdown wrapping
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
            
        resources = json.loads(ai_response)
        
        return jsonify({
            'success': True,
            'resources': resources
        })
    except Exception as e:
        # Fallback to a simple search URL if AI fails
        return jsonify({
            'success': True,
            'resources': [
                {'title': f'Search for {step_title}', 'type': 'Article', 'url': f'https://www.google.com/search?q={topic}+{step_title}'}
            ]
        })

@app.route('/api/generate-assessment', methods=['POST'])
def generate_assessment():
    """Generate career assessment questions"""
    try:
        prompt = """Create a comprehensive career path assessment test. 
        Generate 10 questions that help identify a person's interests, strengths, and ideal career domain (e.g., Software Engineering, Data Science, Cyber Security, UI/UX Design, Digital Marketing, Artificial Intelligence).
        For each question, provide 4 distinct options that map toward different career paths.
        
        Format your response EXACTLY as a JSON list of objects:
        [
          {
            "id": 1,
            "question": "Question text here",
            "options": {
              "A": "Option A text",
              "B": "Option B text",
              "C": "Option C text",
              "D": "Option D text"
            }
          },
          ...
        ]
        Return ONLY the JSON list."""
        
        messages = [{"role": "user", "content": prompt}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content']
        
        # Extract JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
            
        questions = json.loads(ai_response)
        
        return jsonify({
            'success': True,
            'questions': questions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-assessment', methods=['POST'])
def analyze_assessment():
    """Analyze assessment answers and suggest a career domain"""
    data = request.json
    answers = data.get('answers')
    questions = data.get('questions')
    
    if not answers or not questions:
        return jsonify({'error': 'Answers and questions are required'}), 400
        
    try:
        # Prepare data for AI analysis
        analysis_data = []
        for i, q in enumerate(questions):
            ans_key = answers.get(str(i))
            if ans_key:
                analysis_data.append({
                    "question": q['question'],
                    "answer": q['options'][ans_key]
                })
        
        prompt = f"""Based on the following career assessment answers, recommend the single best career domain for this user.
        Consider these domains: Software Engineering, Data Science, Cyber Security, UI/UX Design, Digital Marketing, Artificial Intelligence, Product Management.
        
        Answers:
        {json.dumps(analysis_data, indent=2)}
        
        Return your response EXACTLY as a JSON object:
        {{
          "recommendedDomain": "Domain Name",
          "explanation": "Brief 2-3 sentence explanation of why this fits.",
          "startingTopic": "The best technical topic to start with (e.g., 'Python Programming' for Data Science)"
        }}
        Return ONLY the JSON object."""
        
        messages = [{"role": "user", "content": prompt}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content']
        
        # Extract JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
            
        result = json.loads(ai_response)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-chat', methods=['POST'])
def clear_chat():
    """Clear chat history for current step"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({'error': 'No active session'}), 400
    
    learning_session = sessions[session_id]
    
    if topic_id:
        db.clear_chat_history(int(topic_id), learning_session.current_step_index)
        return jsonify({'success': True})
    
    return jsonify({'error': 'No topic selected'}), 400

@app.route('/resume-analyzer')
def resume_analyzer():
    return render_template('resume.html')

@app.route('/api/analyze-resume', methods=['POST'])
def analyze_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        text = ""
        if file.filename.endswith('.pdf'):
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
        elif file.filename.endswith('.docx'):
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        if len(text.strip()) < 50:
            return jsonify({'error': 'Could not extract enough text from resume'}), 400

        # AI Analysis
        prompt = f"""You are an expert ATS (Applicant Tracking System) and Career Coach. 
        Analyze the following resume text and provide a detailed review.
        
        Resume Content:
        {text[:4000]} # Limit text for API tokens
        
        Return your response EXACTLY as a JSON object:
        {{
          "atsScore": 85, (a number between 0-100)
          "verdict": "Strong Match", (e.g., Needs Work, Fair, Strong Match, Elite)
          "verdictText": "One sentence summary about ATS compatibility.",
          "strengths": ["list of 3 points"],
          "improvements": ["list of 3 points"],
          "recommendations": ["list of 3 points"]
        }}
        Return ONLY the JSON object."""
        
        messages = [{"role": "user", "content": prompt}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content']
        
        # Extract JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
            
        analysis = json.loads(ai_response)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/job-market')
def job_market():
    return render_template('market.html')

@app.route('/mock-test')
def mock_test():
    return render_template('mock_test.html')

@app.route('/progress')
def progress():
    return render_template('progress.html')

@app.route('/api/generate-mock-test', methods=['POST'])
def generate_mock_test():
    session_id = request.cookies.get('session_id')
    topic_id = request.cookies.get('topic_id')
    
    domain = "Software Engineering"  # Default
    if session_id in sessions:
        domain = sessions[session_id].roadmap.topic
    elif topic_id:
        topic_data = db.get_topic(int(topic_id))
        if topic_data:
            domain = topic_data['name']
            
    try:
        test_data = mock_test_gen.generate_mock_test(domain)
        return jsonify({
            'success': True,
            'data': test_data,
            'domain': domain
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/evaluate-mock-test', methods=['POST'])
def evaluate_mock_test():
    data = request.json
    topic = data.get('topic')
    mcq_answers = data.get('mcq_answers', {})
    subjective_answers = data.get('subjective_answers', {})
    questions = data.get('questions')
    
    if not questions:
        return jsonify({'error': 'Questions are required for evaluation'}), 400
        
    try:
        results = mock_test_gen.evaluate_test(topic, mcq_answers, subjective_answers, questions)
        
        # Save results to database
        if topic_id:
            db.save_mock_test_result(int(topic_id), results)
            
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress-report', methods=['GET'])
def get_progress_report():
    """Generate a comprehensive progress report using AI"""
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    if not topic_id:
        return jsonify({'error': 'No topic selected'}), 400
        
    try:
        topic_data = db.get_topic(int(topic_id))
        quiz_results = db.get_quiz_results(int(topic_id))
        mock_results = db.get_mock_test_results(int(topic_id))
        
        # Prepare context for AI
        report_context = {
            "domain": topic_data['name'],
            "total_steps": topic_data['total_steps'],
            "current_step": topic_data['current_step'],
            "quizzes": quiz_results,
            "mock_tests": mock_results
        }
        
        prompt = f"""Analyze the following learning progress for the domain "{topic_data['name']}" and provide a career readiness report.
        
        Data:
        {json.dumps(report_context, indent=2)}
        
        Based on this data, provide:
        1. A "readinessScore" (0-100).
        2. A "status" (e.g., "Learning", "Ready", "Expert").
        3. A list of "softSkills" the user should focus on for this specific domain.
        4. A "summary" of their journey and what's next.
        
        Return your response EXACTLY as a JSON object:
        {{
          "readinessScore": 75,
          "status": "Ready to Apply",
          "softSkills": ["Communication", "Problem Solving", "Time Management"],
          "summary": "You have completed most of the roadmap with high scores...",
          "nextSteps": "Complete the final project and start applying for junior roles."
        }}
        Return ONLY the JSON object."""
        
        messages = [{"role": "user", "content": prompt}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content']
        
        # Extract JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
            
        report = json.loads(ai_response)
        
        return jsonify({
            'success': True,
            'report': report,
            'raw_data': report_context
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/job-market-data', methods=['GET'])
def get_job_market_data():
    topic_id = request.cookies.get('topic_id')
    session_id = request.cookies.get('session_id')
    
    # Get the current domain/topic context
    domain = "Software Engineering" # Default
    if session_id in sessions:
        domain = sessions[session_id].roadmap.topic
    elif topic_id:
        topic_data = db.get_topic(int(topic_id))
        if topic_data:
            domain = topic_data['name']

    try:
        prompt = f"""Provide a real-time comprehensive job market analysis for the domain: {domain} and general tech trends for 2026.
        
        TASK: Find 3 ACTUAL internships and 3 ACTUAL job openings for {domain}.
        
        LINK RELIABILITY RULES:
        1. INTERNSHIPS: Try to provide direct URLs.
        2. JOBS: To prevent "No Match Found", use these exact search templates if a direct URL is unavailable:
           - LinkedIn: https://www.linkedin.com/jobs/search/?keywords={{Job+Title}}+at+{{Company}}
           - Indeed: https://www.indeed.com/jobs?q={{Job+Title}}+{{Company}}
        3. Replace {{Job+Title}} and {{Company}} with the actual values (use + for spaces).
        4. ONLY return legitimate, currently active companies.
        
        Return your response EXACTLY as a JSON object with this structure:
        {{
          "trends": {{
            "labels": ["Domain 1", "Domain 2", "Domain 3", "Domain 4", "Domain 5"],
            "values": [number1-100, number2-100, number3-100, number4-100, number5-100]
          }},
          "domainTraffic": {{
            "labels": ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
            "values": [number1, number2, number3, number4, number5, number6]
          }},
          "salaries": {{
            "fresher": "$60k - $80k",
            "experienced": "$120k - $180k"
          }},
          "summaryNews": "A 3-4 sentence paragraph summarizing current market sentiment, hiring trends, and news for {domain}.",
          "internships": [
            {{
              "title": "Verified Internship Title",
              "company": "Company Name",
              "location": "Location",
              "platform": "LinkedIn or Indeed",
              "url": "application_or_search_url"
            }}
          ],
          "jobs": [
            {{
              "title": "Verified Job Title",
              "company": "Company Name",
              "location": "Location",
              "platform": "LinkedIn or Indeed",
              "url": "application_or_search_url"
            }}
          ]
        }}
        Ensure the 'values' are realistic demand scores based on 2026 data.
        Return ONLY the JSON object."""
        
        messages = [{"role": "user", "content": prompt}]
        response = perplexity_client.chat_completion(messages)
        ai_response = response['choices'][0]['message']['content']
        
        # Extract JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
            
        data = json.loads(ai_response)
        data['domain'] = domain
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(host=host, port=port, debug=debug)
