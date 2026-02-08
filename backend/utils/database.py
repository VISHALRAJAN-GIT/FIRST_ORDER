import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.getenv('DATABASE_PATH', 'learning_assistant.db')

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Topics table
    c.execute('''CREATE TABLE IF NOT EXISTS topics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  total_steps INTEGER,
                  current_step INTEGER DEFAULT 0,
                  completed BOOLEAN DEFAULT 0,
                  roadmap_data TEXT)''')
    
    # Progress table
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_id INTEGER,
                  step_number INTEGER,
                  completed BOOLEAN DEFAULT 0,
                  time_spent INTEGER DEFAULT 0,
                  completed_at TIMESTAMP,
                  FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    
    # Notes table
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_id INTEGER,
                  step_number INTEGER,
                  content TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    
    # Chat history table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_id INTEGER,
                  step_number INTEGER,
                  role TEXT,
                  message TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    
    # Quiz results table
    c.execute('''CREATE TABLE IF NOT EXISTS quiz_results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic_id INTEGER,
                  step_number INTEGER,
                  score INTEGER,
                  total_questions INTEGER,
                  completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (topic_id) REFERENCES topics(id))''')
    
    conn.commit()
    conn.close()

def save_topic(name, roadmap_data, total_steps):
    """Save a new topic to the database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO topics (name, total_steps, roadmap_data)
                 VALUES (?, ?, ?)''', (name, total_steps, json.dumps(roadmap_data)))
    
    topic_id = c.lastrowid
    
    # Initialize progress for all steps
    for i in range(total_steps):
        c.execute('''INSERT INTO progress (topic_id, step_number)
                     VALUES (?, ?)''', (topic_id, i))
    
    conn.commit()
    conn.close()
    return topic_id

def get_all_topics():
    """Get all topics"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, name, total_steps, current_step, completed, last_accessed
                 FROM topics ORDER BY last_accessed DESC''')
    
    topics = []
    for row in c.fetchall():
        topics.append({
            'id': row[0],
            'name': row[1],
            'total_steps': row[2],
            'current_step': row[3],
            'completed': bool(row[4]),
            'last_accessed': row[5]
        })
    
    conn.close()
    return topics

def get_topic(topic_id):
    """Get a specific topic"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, name, total_steps, current_step, roadmap_data
                 FROM topics WHERE id = ?''', (topic_id,))
    
    row = c.fetchone()
    if row:
        topic = {
            'id': row[0],
            'name': row[1],
            'total_steps': row[2],
            'current_step': row[3],
            'roadmap_data': json.loads(row[4])
        }
    else:
        topic = None
    
    conn.close()
    return topic

def update_topic_progress(topic_id, step_number):
    """Update the current step for a topic"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''UPDATE topics SET current_step = ?, last_accessed = CURRENT_TIMESTAMP
                 WHERE id = ?''', (step_number, topic_id))
    
    conn.commit()
    conn.close()

def save_note(topic_id, step_number, content):
    """Save or update a note"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if note exists
    c.execute('''SELECT id FROM notes WHERE topic_id = ? AND step_number = ?''',
              (topic_id, step_number))
    
    if c.fetchone():
        c.execute('''UPDATE notes SET content = ?, updated_at = CURRENT_TIMESTAMP
                     WHERE topic_id = ? AND step_number = ?''',
                  (content, topic_id, step_number))
    else:
        c.execute('''INSERT INTO notes (topic_id, step_number, content)
                     VALUES (?, ?, ?)''', (topic_id, step_number, content))
    
    conn.commit()
    conn.close()

def get_note(topic_id, step_number):
    """Get a note for a specific step"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT content FROM notes WHERE topic_id = ? AND step_number = ?''',
              (topic_id, step_number))
    
    row = c.fetchone()
    note = row[0] if row else None
    
    conn.close()
    return note

def save_chat_message(topic_id, step_number, role, message):
    """Save a chat message"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO chat_history (topic_id, step_number, role, message)
                 VALUES (?, ?, ?, ?)''', (topic_id, step_number, role, message))
    
    conn.commit()
    conn.close()

def get_chat_history(topic_id, step_number, limit=10):
    """Get chat history for a step"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT role, message, created_at FROM chat_history
                 WHERE topic_id = ? AND step_number = ?
                 ORDER BY created_at DESC LIMIT ?''',
              (topic_id, step_number, limit))
    
    messages = []
    for row in c.fetchall():
        messages.append({
            'role': row[0],
            'message': row[1],
            'created_at': row[2]
        })
    
    conn.close()
    return list(reversed(messages))

def clear_chat_history(topic_id, step_number):
    """Clear chat history for a specific step"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''DELETE FROM chat_history 
                 WHERE topic_id = ? AND step_number = ?''',
              (topic_id, step_number))
    
    conn.commit()
    conn.close()

def save_quiz_result(topic_id, step_number, score, total_questions):
    """Save quiz results"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO quiz_results (topic_id, step_number, score, total_questions)
                 VALUES (?, ?, ?, ?)''', (topic_id, step_number, score, total_questions))
    
    conn.commit()
    conn.close()

def get_quiz_results(topic_id):
    """Get all quiz results for a topic"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT step_number, score, total_questions, completed_at
                 FROM quiz_results WHERE topic_id = ?
                 ORDER BY step_number''', (topic_id,))
    
    results = []
    for row in c.fetchall():
        results.append({
            'step_number': row[0],
            'score': row[1],
            'total_questions': row[2],
            'completed_at': row[3]
        })
    
    conn.close()
    return results

# Initialize database on import
init_db()
