import os
import re
import io
import csv
import json
import uuid
import random
import base64
import unicodedata
import urllib.request
import urllib.error
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

def escape_dollars(text) -> str:
    """Escapes unescaped dollar signs so Streamlit does not render text between them as LaTeX math."""
    if text is None:
        return ""
    return re.sub(r'(?<!\\)\$', r'\\$', str(text))

def strip_accents(text: str) -> str:
    """Strips accents from characters for accent-tolerant matching."""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def normalize_italian(text: str) -> str:
    """Normalizes Italian text, handling apostrophe-based accents like e' -> è."""
    if text is None:
        return ""
    t = str(text).strip().lower().replace("’", "'").replace("`", "'")
    t = re.sub(r"([aeiou])\s*'", r"\1'", t)
    apostrophe_map = {
        "e'": "è",
        "a'": "à",
        "i'": "ì",
        "o'": "ò",
        "u'": "ù",
    }
    for k, v in apostrophe_map.items():
        t = t.replace(k, v)
    return t.strip(" .?!,;:'\"")

def check_answer(user_ans, correct_ans, is_free_text: bool = False, is_italian: bool = False) -> tuple[bool, bool]:
    """
    Checks user answer against correct answer.
    Returns (is_correct, is_accent_tip)
    """
    if user_ans is None or str(user_ans).strip() == "":
        return False, False
        
    if not is_free_text:
        return (user_ans == correct_ans, False)
        
    u_str = str(user_ans).strip().lower().strip(" .?!,;:'\"")
    c_str = str(correct_ans).strip().lower().strip(" .?!,;:'\"")
    
    if u_str == c_str:
        return True, False
        
    if is_italian:
        u_norm = normalize_italian(user_ans)
        c_norm = normalize_italian(correct_ans)
        
        if u_norm == c_norm:
            return True, False
            
        if strip_accents(u_norm) == strip_accents(c_norm):
            return True, True
            
    return False, False

# 1. Open the secure vault and grab the key
load_dotenv()
my_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=my_key)

st.set_page_config(page_title="Study Prep", page_icon="🚀", layout="wide")
st.title("🚀 AI Study Prep Engine")

# --- PROFILE & PROGRESS TRACKER FUNCTIONS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_FILE = os.path.join(BASE_DIR, "profile.json")
GITHUB_REPO = "MelTaz/Leonardo-Study-Engine"
GITHUB_BRANCH = "data"

def get_github_token():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        try:
            token = st.secrets.get("GITHUB_TOKEN")
        except Exception:
            token = None
    return token

def load_profile_from_github(token=None) -> dict:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/profile.json?ref={GITHUB_BRANCH}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Leonardo-Study-Engine"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            content_b64 = data.get("content", "")
            json_text = base64.b64decode(content_b64).decode('utf-8-sig')
            parsed = json.loads(json_text)
            if "summary" not in parsed:
                return {"summary": parsed, "history": []}
            return parsed
    except Exception:
        return None

def generate_history_csv(profile_data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Topic", "Difficulty", "Score", "Total", "Accuracy %", "Mistakes Count", "Missed Questions Summary"])
    for log in reversed(profile_data.get("history", [])):
        tot = log.get("total", 0)
        sc = log.get("score", 0)
        acc = f"{int((sc / tot) * 100)}%" if tot > 0 else "0%"
        m = log.get("mistakes", [])
        m_sum = "; ".join([f"{item.get('question', '')} [Selected: {item.get('selected', '')}, Correct: {item.get('correct', '')}]" for item in m])
        writer.writerow([
            log.get("date", ""),
            log.get("topic", ""),
            log.get("difficulty", ""),
            sc,
            tot,
            acc,
            len(m),
            m_sum
        ])
    return output.getvalue()

def save_profile_to_github_squashed(token: str, profile_data: dict) -> bool:
    if not token:
        return False
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Leonardo-Study-Engine",
        "Content-Type": "application/json"
    }
    try:
        # 1. Create blob for profile.json
        json_str = json.dumps(profile_data, indent=4)
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/blobs",
            data=json.dumps({"content": json_str, "encoding": "utf-8"}).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            json_blob_sha = json.loads(resp.read().decode('utf-8'))["sha"]
            
        # 2. Create blob for profile_history.csv
        csv_str = generate_history_csv(profile_data)
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/blobs",
            data=json.dumps({"content": csv_str, "encoding": "utf-8"}).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            csv_blob_sha = json.loads(resp.read().decode('utf-8'))["sha"]
            
        # 3. Create tree containing both blobs
        tree_payload = {
            "tree": [
                {"path": "profile.json", "mode": "100644", "type": "blob", "sha": json_blob_sha},
                {"path": "profile_history.csv", "mode": "100644", "type": "blob", "sha": csv_blob_sha}
            ]
        }
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/trees",
            data=json.dumps(tree_payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            tree_sha = json.loads(resp.read().decode('utf-8'))["sha"]
            
        # 4. Create standalone commit with no parents (permanently squashed!)
        commit_payload = {
            "message": "Update study profile [skip ci]",
            "tree": tree_sha,
            "parents": []
        }
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/commits",
            data=json.dumps(commit_payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            new_commit_sha = json.loads(resp.read().decode('utf-8'))["sha"]
            
        # 5. Force update refs/heads/data to point to new commit
        ref_payload = {
            "sha": new_commit_sha,
            "force": True
        }
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/{GITHUB_BRANCH}",
            data=json.dumps(ref_payload).encode('utf-8'),
            headers=headers,
            method="PATCH"
        )
        with urllib.request.urlopen(req) as resp:
            return True
    except Exception as e:
        print(f"Error saving to GitHub: {e}")
        return False

def load_profile():
    token = get_github_token()
    cloud_data = load_profile_from_github(token)
    if cloud_data is not None:
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(cloud_data, f, indent=4)
        except Exception:
            pass
        return cloud_data
        
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if "summary" not in data:
                    return {"summary": data, "history": []}
                return data
        except Exception:
            return {"summary": {}, "history": []}
    return {"summary": {}, "history": []}

def save_profile(profile):
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=4)
    except Exception:
        pass
        
    token = get_github_token()
    if token:
        save_profile_to_github_squashed(token, profile)

profile_data = load_profile()

# 2. App Memory (Session State)
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "quiz_subject" not in st.session_state:
    st.session_state.quiz_subject = ""
if "quiz_difficulty" not in st.session_state:
    st.session_state.quiz_difficulty = ""
if "quiz_id" not in st.session_state:
    st.session_state.quiz_id = str(uuid.uuid4())

# Official list of active subjects
ALLOWED_SUBJECTS = [
    "Maths ICAS Prep",
    "Fractions",
    "Proofreading (Grammar and Punctuation)",
    "Spelling",
    "Multiplication and Division",
    "Italian"
]

# --- CREATE TABS ---
tab1, tab2 = st.tabs(["🎓 Leonardo's Zone", "📊 Parent Dashboard"])

# ==========================================
# TAB 1: THE STUDENT ZONE
# ==========================================
with tab1:
    st.header("Welcome back, Leonardo! 🚀")
    
    col1, col2 = st.columns(2)
    with col1:
        subject_focus = st.selectbox(
            "What topic to practice today?", 
            ALLOWED_SUBJECTS
        )
    with col2:
        difficulty = st.selectbox("Select Difficulty Level", ["1 - Easy", "2 - Medium", "3 - Hard", "Mix of all levels"])

    # --- LEVEL UP TRIGGER ---
    recent_logs = [log for log in profile_data["history"] if log["topic"] == subject_focus]
    if len(recent_logs) >= 2:
        last_1 = recent_logs[-1]
        last_2 = recent_logs[-2]
        
        if (last_1.get("difficulty") == difficulty and last_2.get("difficulty") == difficulty):
            if last_1.get("total", 0) > 0 and last_2.get("total", 0) > 0:
                score1 = last_1["score"] / last_1["total"]
                score2 = last_2["score"] / last_2["total"]
                
                if score1 >= 0.9 and score2 >= 0.9:
                    if difficulty == "1 - Easy":
                        st.info("🌟 **You are crushing Easy!** The Wizard thinks you are ready to try **Medium**!")
                    elif difficulty == "2 - Medium":
                        st.success("🔥 **You are mastering Medium!** Are you brave enough to challenge the Wizard on **Hard**?")

    if st.button("Generate Quiz"):
        st.session_state.quiz_id = str(uuid.uuid4())
                
        with st.spinner(f"Generating 10 {subject_focus} questions..."):
            
            # --- CLEAN SLATE ADAPTIVE AI LOGIC ---
            history_context = ""
            if subject_focus in profile_data["summary"]:
                stats = profile_data["summary"][subject_focus]
                total_q = stats.get("total_questions", 0)
                total_c = stats.get("total_correct", 0)
                acc = int((total_c / total_q) * 100) if total_q > 0 else 0
                history_context = f"\nHistorical performance on '{subject_focus}': {acc}% overall accuracy."
                
                recent_mistakes = []
                for log in reversed(profile_data["history"]):
                    if log["topic"] == subject_focus and log.get("difficulty") == difficulty and log["mistakes"]:
                        for mistake in log["mistakes"]:
                            recent_mistakes.append(mistake["question"])
                        
                        if len(recent_mistakes) >= 5:
                            break
                            
                if recent_mistakes:
                    history_context += f"\nHe recently answered '{difficulty}' questions similar to these incorrectly:\n"
                    for m in recent_mistakes[:5]:
                        history_context += f"- {m}\n"
                    history_context += "Design new questions that specifically test the underlying concepts he missed in those examples."
                else:
                    history_context += f"\nHe has a clean slate for '{difficulty}' level! Test his baseline knowledge."

            # --- SUBJECT-SPECIFIC RULES ---
            subject_rules = ""
            if subject_focus == "Italian":
                subject_rules = """
            SPECIAL RULES FOR ITALIAN (BILINGUAL SCHOOL STUDENT):
            - Leonardo attends an Italian bilingual school. Do NOT treat him as an absolute beginner; NEVER test isolated single-word flashcards (e.g., do NOT ask 'What is dog in Italian?').
            - NEVER include English translations in brackets next to Italian words in questions or options. Use Italian context or natural scenario prompts.
            - If difficulty is '1 - Easy' (Solid A1 Conversational & Everyday Language):
              * Realistic dialogues and conversational exchanges (e.g., greetings, how to introduce someone, asking personal questions like 'Di dove sei?' or 'Quanti anni hai?').
              * Everyday situational responses (e.g., expressing needs like 'ho fame' / 'ho sete', asking permission like 'Posso...?').
              * Core verbs in sentence context (essere, avere, high-frequency regular verbs), and gender/plural agreements for articles and adjectives.
            - If difficulty is '2 - Medium' (Upper A1 / Early A2 - Sentences & Routines):
              * Expressing preferences with explanations ('Ti piace...?' / 'Sì, mi piace... perché...').
              * Daily routines, telling time, school activities, and prepositions (a, in, da, con, per).
              * Question words (Chi, Che cosa, Dove, Quando, Perché, Come) and logical sentence completion.
            - If difficulty is '3 - Hard' (Solid A2 - Mini-Stories & Reading Comprehension):
              * Present a short 2–3 sentence mini-story or scenario in Italian, followed by a comprehension question in Italian (e.g., 'Dove va Giulia dopo la scuola?').
              * Conjunctions (mentre, ma, perché, quindi) and common past tense (passato prossimo with essere/avere, e.g., 'ho mangiato', 'è andato').
            - For any 'free_text' questions, ensure the expected correct_answer is concise (1 to 3 words, such as 'è', 'perché', 'al parco', 'ho finito') so a Year 3 student can type it easily.
            """
            elif subject_focus == "Fractions":
                subject_rules = """
            SPECIAL RULES FOR FRACTIONS:
            - Do NOT use confusing emojis to represent fractions. 
            - Instead, embed helpful drawing hints directly into the question or explanation (e.g., "Hint: Try drawing a shape or a bar on paper to help you solve this!").
            """
                if difficulty == "1 - Easy":
                    subject_rules += "- Include a drawing prompt or hint in almost every question, helping him visualize shapes, chocolate bars, or groups of objects."
                elif difficulty == "2 - Medium":
                    subject_rules += "- Mix standard word problems with occasional drawing hints."
                elif difficulty == "3 - Hard":
                    subject_rules += "- Focus on abstract numerical fractions and complex multi-step word problems without drawing hints."

            # --- PROMPT ---
            prompt = f"""
            Generate 10 practice questions for a Year 3 student. 
            Topic: {subject_focus}
            Difficulty Level: {difficulty}
            {history_context}
            {subject_rules}

            IMPORTANT FORMATTING RULE:
            If the Topic is 'Spelling' or 'Italian', please generate a mix of 'multiple_choice' and 'free_text' questions. 
            For all other topics, generate ONLY 'multiple_choice' questions.

            Return the result strictly as a JSON list where each item has:
            - "type": strictly either "multiple_choice" or "free_text"
            - "question": The text of the question
            - "options": A list of 4 multiple-choice options (leave as an empty list [] if type is free_text)
            - "correct_answer": The exact correct answer. If free_text, provide the exact word or phrase they should type.
            - "explanation": A brief, encouraging explanation of the answer
            """
            
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            st.session_state.quiz_data = json.loads(response.text)
            st.session_state.quiz_subject = subject_focus
            st.session_state.quiz_difficulty = difficulty 

    # Display the Interactive Quiz
    if st.session_state.quiz_data:
        st.divider()
        st.subheader(f"📝 Practice Quiz: {st.session_state.quiz_subject} ({st.session_state.quiz_difficulty})")
        
        user_answers = {}
        for i, q in enumerate(st.session_state.quiz_data):
            st.write(f"**Question {i+1}:** {escape_dollars(q['question'])}")
            
            unique_key = f"q_{st.session_state.quiz_id}_{i}"
            
            if q.get('type') == 'free_text':
                if st.session_state.quiz_subject == "Italian":
                    st.caption("💡 *Tip: To write an accent, just type an apostrophe after the letter (e.g. type **e'** for **è**).*")
                    input_label = "Type your answer in Italian (Scrivi in italiano):"
                    input_placeholder = "Scrivi la risposta in italiano qui..."
                else:
                    input_label = "Type your answer here:"
                    input_placeholder = ""
                user_answers[i] = st.text_input(input_label, placeholder=input_placeholder, key=unique_key)
            else:
                user_answers[i] = st.radio("Choose an answer:", q['options'], key=unique_key, index=None, format_func=escape_dollars)
            
            st.write("---")
            
        if st.button("Submit Answers"):
            score = 0
            total_questions = len(st.session_state.quiz_data)
            incorrect_summary = [] 
            is_italian = (st.session_state.quiz_subject == "Italian")
            
            st.subheader("📊 Quiz Feedback")
            
            for i, q in enumerate(st.session_state.quiz_data):
                clean_q = escape_dollars(q['question'])
                clean_exp = escape_dollars(q['explanation'])
                clean_correct = escape_dollars(q['correct_answer'])
                
                user_ans = user_answers[i]
                is_free = (q.get('type') == 'free_text')
                is_correct, is_accent_tip = check_answer(
                    user_ans=user_ans,
                    correct_ans=q['correct_answer'],
                    is_free_text=is_free,
                    is_italian=is_italian
                )

                if is_correct:
                    score += 1
                    if is_accent_tip:
                        st.success(f"**Question {i+1}: Spot on! 🎉** *(Tip: In Italian, remember the accent: **{clean_correct}**)* \n\n*Why it's right:* {clean_exp}")
                    else:
                        st.success(f"**Question {i+1}: Spot on! 🎉** \n\n*Why it's right:* {clean_exp}")
                elif user_ans is None or str(user_ans).strip() == "":
                    st.warning(f"**Question {i+1}: You skipped this one!** The correct answer is **{clean_correct}**. \n\n*Helpful tip:* {clean_exp}")
                    incorrect_summary.append({
                        "question": clean_q,
                        "selected": "Skipped",
                        "correct": clean_correct,
                        "explanation": clean_exp
                    })
                else:
                    user_ans_clean = escape_dollars(user_ans)
                    st.info(f"**Question {i+1}: Good try, but not quite!** The correct answer is **{clean_correct}**. \n\n*Helpful tip:* {clean_exp}")
                    incorrect_summary.append({
                        "question": clean_q,
                        "selected": user_ans_clean,
                        "correct": clean_correct,
                        "explanation": clean_exp
                    })
                
            st.write("---")
            st.subheader(f"Final Score: {score} out of {total_questions} 🌟")
            
            # --- NEW DYNAMIC ENCOURAGEMENT LOGIC ---
            percentage = score / total_questions if total_questions > 0 else 0
            
            if percentage == 1.0:
                st.balloons()
                emoji = "🧙‍♂️✨🏆"
                title = "Behold! The Wizard of Wisdom says:"
                messages = [
                    "A PERFECT SCORE! Your brain power is unmatched, Leonardo! Fantastic job!",
                    "Flawless victory! Are you sure you're not a supercomputer in disguise?",
                    "100%! The Wizard is taking notes from YOU now, Leonardo!"
                ]
                bg_color = "#d4edda" # Triumphant Green
                
            elif percentage >= 0.8:
                st.balloons()
                emoji = "🚀🔥"
                title = "Incredible work, Leonardo!"
                messages = [
                    "Almost perfect! The Wizard is highly impressed with your skills.",
                    "You are absolutely crushing it! Just a tiny step away from a perfect score.",
                    "Amazing job! Your brain is growing stronger every second!"
                ]
                bg_color = "#cce5ff" # Heroic Blue
                
            elif percentage >= 0.5:
                emoji = "🧠⚡"
                title = "Great effort, Leonardo!"
                messages = [
                    "Solid work! You're getting the hang of this. Let's try another one and beat this score!",
                    "Not bad at all! Every question you answer makes you smarter. Ready for round two?",
                    "The Wizard sees your potential! A little more practice and you'll be unstoppable!"
                ]
                bg_color = "#fff3cd" # Encouraging Yellow
                
            else:
                emoji = "💪🌱"
                title = "Keep pushing, Leonardo!"
                messages = [
                    "Every master was once a beginner! Mistakes just mean you're learning. Let's try again!",
                    "The Wizard says: 'Even the strongest wizards need practice!' Give it another go!",
                    "A tough one, but you didn't give up! Let's do another quiz and level up your brain!"
                ]
                bg_color = "#f8d7da" # Motivating Red (light)

            # Pick a random message from the chosen tier
            selected_message = random.choice(messages)

            # Display the dynamic feedback card
            st.markdown(f"""
            <div style="text-align: center; background-color: {bg_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h1 style="font-size: 80px; margin: 0;">{emoji}</h1>
                <h2 style="color: #333;">{title}</h2>
                <h3 style="color: #444; font-style: italic;">"{selected_message}"</h3>
            </div>
            """, unsafe_allow_html=True)
            # --- END NEW LOGIC ---

            # Continue with your existing code saving the log to the profile...
            topic = st.session_state.quiz_subject
            diff = st.session_state.quiz_difficulty
            
            if topic not in profile_data["summary"]:
                profile_data["summary"][topic] = {"total_questions": 0, "total_correct": 0}
            profile_data["summary"][topic]["total_questions"] += total_questions
            profile_data["summary"][topic]["total_correct"] += score
            
            current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
            quiz_log = {
                "date": current_time,
                "topic": topic,
                "difficulty": diff, 
                "score": score,
                "total": total_questions,
                "mistakes": incorrect_summary
            }
            profile_data["history"].append(quiz_log)
            save_profile(profile_data)

# ==========================================
# TAB 2: THE PARENT DASHBOARD
# ==========================================
with tab2:
    st.header("📊 Parent Review Dashboard")
    st.write("Review recent quizzes and focus areas below.")
    
    st.subheader("Topic Mastery")
    # Filter summary data to only show allowed subjects
    filtered_summary = {k: v for k, v in profile_data["summary"].items() if k in ALLOWED_SUBJECTS}
    
    if filtered_summary:
        for topic, stats in filtered_summary.items():
            attempts = stats.get("total_questions", 0)
            correct = stats.get("total_correct", 0)
            accuracy = int((correct / attempts) * 100) if attempts > 0 else 0
            
            st.markdown(f"**{topic}**: {accuracy}% Accuracy ({correct}/{attempts} correct)")
            st.progress(accuracy / 100)
    else:
        st.info("No summary data available yet.")
        
    st.divider()
    
    st.subheader("Recent Activity Log")
    # Filter history logs to only show allowed subjects
    filtered_history = [log for log in profile_data["history"] if log.get("topic") in ALLOWED_SUBJECTS]
    
    if filtered_history:
        for log in reversed(filtered_history):
            diff_label = log.get('difficulty', 'Unknown Level')
            with st.expander(f"{log['date']} - {log['topic']} ({diff_label}) - Score: {log['score']}/{log['total']}"):
                if log['mistakes']:
                    st.error(f"Areas to Review ({len(log['mistakes'])} missed/skipped):")
                    for mistake in log['mistakes']:
                        st.write(f"**Q:** {escape_dollars(mistake['question'])}")
                        st.write(f"❌ **Selected:** {escape_dollars(mistake['selected'])}")
                        st.write(f"✅ **Correct:** {escape_dollars(mistake['correct'])}")
                        st.caption(f"*AI Note:* {escape_dollars(mistake['explanation'])}")
                        st.write("---")
                else:
                    st.success("Perfect score! No mistakes to review.")
    else:
        st.info("No recent quizzes have been completed.")