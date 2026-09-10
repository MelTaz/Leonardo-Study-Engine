import os
import json
import uuid
import random
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Open the secure vault and grab the key
load_dotenv()
my_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=my_key)

st.set_page_config(page_title="Study Prep", page_icon="🚀", layout="wide")
st.title("🚀 AI Study Prep Engine")

# --- PROFILE & PROGRESS TRACKER FUNCTIONS ---
PROFILE_FILE = "profile.json"

def load_profile():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r") as f:
                data = json.load(f)
                if "summary" not in data:
                    return {"summary": data, "history": []}
                return data
        except Exception:
            return {"summary": {}, "history": []}
    return {"summary": {}, "history": []}

def save_profile(profile):
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=4)

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
            SPECIAL RULES FOR ITALIAN:
            - NEVER include English translations in brackets next to the Italian words in the questions or the options.
            - If difficulty is '1 - Easy' or '2 - Medium', focus on vocabulary, basic verbs, and simple sentence translation without giving hints.
            - If difficulty is '3 - Hard', make the questions conversational (e.g., how to respond to a specific Italian prompt, completing a realistic dialogue, or understanding the context of a conversation).
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
            st.write(f"**Question {i+1}:** {q['question']}")
            
            unique_key = f"q_{st.session_state.quiz_id}_{i}"
            
            if q.get('type') == 'free_text':
                user_answers[i] = st.text_input("Type your answer here:", key=unique_key)
            else:
                user_answers[i] = st.radio("Choose an answer:", q['options'], key=unique_key, index=None)
            
            st.write("---")
            
        if st.button("Submit Answers"):
            score = 0
            total_questions = len(st.session_state.quiz_data)
            incorrect_summary = [] 
            
            st.subheader("📊 Quiz Feedback")
            
            for i, q in enumerate(st.session_state.quiz_data):
                clean_q = q['question'].replace('$', r'\$')
                clean_exp = q['explanation'].replace('$', r'\$')
                clean_correct = str(q['correct_answer']).replace('$', r'\$')
                
                user_ans = user_answers[i]
                is_correct = False
                
                if user_ans is not None and str(user_ans).strip() != "":
                    if q.get('type') == 'free_text':
                        is_correct = str(user_ans).strip().lower() == str(q['correct_answer']).strip().lower()
                    else:
                        is_correct = user_ans == q['correct_answer']

                if is_correct:
                    score += 1
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
                    user_ans_clean = str(user_ans).replace('$', r'\$')
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
                        st.write(f"**Q:** {mistake['question']}")
                        st.write(f"❌ **Selected:** {mistake['selected']}")
                        st.write(f"✅ **Correct:** {mistake['correct']}")
                        st.caption(f"*AI Note:* {mistake['explanation']}")
                        st.write("---")
                else:
                    st.success("Perfect score! No mistakes to review.")
    else:
        st.info("No recent quizzes have been completed.")