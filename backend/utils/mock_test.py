from backend.api.perplexity import PerplexityClient
import json
import re

class MockTestGenerator:
    def __init__(self):
        self.client = PerplexityClient()

    def generate_mock_test(self, topic):
        """Generate a comprehensive mock test with MCQs and Subjective questions"""
        prompt = f"""Generate a comprehensive mock test for the topic: {topic}.
        
        The test must include:
        1. 5 Multiple Choice Questions (MCQ)
        2. 3 Subjective (Detailed answer) Questions
        
        Format your response EXACTLY as a JSON object:
        {{
          "mcqs": [
            {{
              "id": 1,
              "question": "Question text",
              "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
              "correct": "A"
            }}
          ],
          "subjective": [
            {{
              "id": 1,
              "question": "Detailed question text",
              "guidelines": "What to include in the answer"
            }}
          ]
        }}
        Return ONLY the JSON object."""

        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat_completion(messages, temperature=0.7)
        ai_response = response['choices'][0]['message']['content']
        
        # Extract JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
            
        return json.loads(ai_response)

    def evaluate_test(self, topic, mcq_answers, subjective_answers, questions):
        """Evaluate both MCQ and Subjective answers using AI"""
        
        # Prepare evaluation data
        eval_data = {
            "topic": topic,
            "mcqs": [],
            "subjective": []
        }
        
        # Evaluate MCQs
        mcq_score = 0
        total_mcqs = len(questions['mcqs'])
        for i, q in enumerate(questions['mcqs']):
            user_ans = mcq_answers.get(str(q['id']))
            is_correct = user_ans == q['correct']
            if is_correct:
                mcq_score += 1
            eval_data['mcqs'].append({
                "question": q['question'],
                "user_answer": user_ans,
                "correct_answer": q['correct'],
                "is_correct": is_correct
            })
            
        # Prepare subjective answers for AI
        subjective_for_ai = []
        for i, q in enumerate(questions['subjective']):
            user_ans = subjective_answers.get(str(q['id']))
            subjective_for_ai.append({
                "question": q['question'],
                "user_answer": user_ans
            })
            
        prompt = f"""Evaluate the following subjective answers for a mock test on "{topic}".
        
        Answers:
        {json.dumps(subjective_for_ai, indent=2)}
        
        For each answer, provide:
        1. A score from 0-10.
        2. Constructive feedback.
        3. A "model" key point.
        
        Return your response EXACTLY as a JSON object:
        {{
          "subjective_evaluation": [
            {{
              "id": 1,
              "score": 8,
              "feedback": "...",
              "key_point": "..."
            }}
          ],
          "overall_feedback": "General summary of performance across subjective questions."
        }}
        Return ONLY the JSON object."""

        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat_completion(messages, temperature=0.3)
        ai_eval_response = response['choices'][0]['message']['content']
        
        # Extract JSON
        if "```json" in ai_eval_response:
            ai_eval_response = ai_eval_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_eval_response:
            ai_eval_response = ai_eval_response.split("```")[1].split("```")[0].strip()
            
        subjective_eval = json.loads(ai_eval_response)
        
        # Calculate final results
        result = {
            "mcq_score": mcq_score,
            "total_mcqs": total_mcqs,
            "mcq_details": eval_data['mcqs'],
            "subjective_details": subjective_eval['subjective_evaluation'],
            "overall_feedback": subjective_eval['overall_feedback']
        }
        return result
