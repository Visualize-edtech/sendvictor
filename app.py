# ===================== app.py (RAG-Enhanced) =====================
import gradio as gr
import requests
import os
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import pandas as pd
import re

# === Load Prompts ===
def load_prompts(file_path="prompts.md"):
    with open(file_path, "r") as f:
        content = f.read()
    prompts = {}
    sections = content.split("<!-- ")
    for section in sections[1:]:
        key, text = section.split(" -->", 1)
        prompts[key.strip()] = text.strip()
    return prompts

PROMPTS = load_prompts()

# === SYMP RAG Layer ===
df = pd.read_csv("SYMP.csv")
df = df.dropna(subset=["Preferred Label"]).copy()
df["Preferred Label"] = df["Preferred Label"].str.lower().str.strip()
df["Synonyms"] = df["Synonyms"].fillna("").str.lower()
df["synonym_list"] = df["Synonyms"].apply(lambda x: re.split(r"\\||,", x))

def retrieve_symptom_info(user_symptom):
    user_symptom = user_symptom.lower().strip()
    match = df[df["Preferred Label"] == user_symptom]
    if not match.empty:
        row = match.iloc[0]
        return row["Preferred Label"], row["definition"]
    for _, row in df.iterrows():
        if user_symptom in row["synonym_list"]:
            return row["Preferred Label"], row["definition"]
    return None, None

# === OpenAI Query ===
def evaluate_with_openai(prompt: str, max_tokens: int = 500) -> str:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4", 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {str(e)}"

# === Local Storage ===
def save_onboarding_data(user_id, name, family, chronic, meds, investigations, surgeries, allergies):
    if not user_id.strip():
        return "❌ Error: User ID required.", *(gr.update(),) * 7

    data = {
        "Full Name": name,
        "Family History": family,
        "Chronic Conditions": chronic,
        "Current Medications": meds,
        "Past Investigations": investigations,
        "Past Surgeries": surgeries,
        "Allergies": allergies
    }
    with open(f"onboarding_{user_id}.json", "w") as f:
        json.dump(data, f, indent=2)

    return (
        "✅ Saved and locked.",
        *(gr.update(interactive=False),) * 7
    )

def reset_onboarding_fields():
    return (
        "🔄 You can now edit.",
        *(gr.update(interactive=True),) * 7
    )

def auto_load_onboarding(user_id):
    file_path = f"onboarding_{user_id}.json"
    if not os.path.exists(file_path):
        return ("", *("",) * 7)
    with open(file_path, "r") as f:
        data = json.load(f)
    return (
        "Data loaded.",
        gr.update(value=data.get("Full Name", ""), interactive=False),
        gr.update(value=data.get("Family History", ""), interactive=False),
        gr.update(value=data.get("Chronic Conditions", ""), interactive=False),
        gr.update(value=data.get("Current Medications", ""), interactive=False),
        gr.update(value=data.get("Past Investigations", ""), interactive=False),
        gr.update(value=data.get("Past Surgeries", ""), interactive=False),
        gr.update(value=data.get("Allergies", ""), interactive=False)
    )

def save_user_id_only(user_id):
    if not user_id.strip():
        return "Error: User ID required."
    with open("user_id.json", "w") as f:
        json.dump({"user_id": user_id}, f)
    return "User ID saved."

# === Timeline ===
def name_timeline_file(user_id):
    return f"timeline_{user_id}.json"

def load_timeline(user_id):
    file = name_timeline_file(user_id)
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return []

def save_to_timeline(user_id, entry):
    timeline = load_timeline(user_id)
    timeline.append(entry)
    with open(name_timeline_file(user_id), "w") as f:
        json.dump(timeline, f, indent=2)

def format_timeline(timeline):
    formatted_entries = []
    for t in reversed(timeline):
        if 'symptom' in t and 'followup_answers' in t:
            # New format
            formatted_entries.append(
                f" {t['time']}\nSymptom: {t['symptom']}\nFollow-up Answers: {t['followup_answers']}\nSummary: {t['summary']}\n"
            )
        elif 'presenting complaint' in t and 'follow-up summary' in t:
            # Structured summary format
            formatted_entries.append(
                f" {t['time']}\nPresenting Complaint: {t['presenting complaint']}\nFollow-up Summary: {t['follow-up summary']}\nTags: {t['tags']}\n"
            )
        elif 'raw' in t:
            # Old free-form format
            formatted_entries.append(
                f" {t['time']}\nUser Input:\n{t['raw']}\n\n"
            )
        else:
            formatted_entries.append(
                f" {t['time']}\nUnrecognized format: {json.dumps(t, indent=2)}\n"
            )
    return "\n\n".join(formatted_entries)

def load_user_timeline(user_id):
    if not user_id.strip():
        return "Error: Enter a user ID to load timeline."
    return format_timeline(load_timeline(user_id))

# === RAG-Enhanced Follow-up Questions ===
def ask_followup(user_id, symptom):
    if not user_id.strip() or not symptom.strip():
        return "Error: User ID and symptom required.", "", "", "", "", "", "", ""

    canonical_label, definition = retrieve_symptom_info(symptom)

    def enrich(prompt_key):
        base_prompt = PROMPTS[prompt_key]
        if definition:
            enriched = f"You are an NHS GP in the UK. The patient reports the symptom '{symptom}' defined as: {definition}\nUse this info:\n" + base_prompt
            return evaluate_with_openai(enriched.format(symptom=symptom))
        else:
            return evaluate_with_openai(base_prompt.format(symptom=symptom))

    q = enrich("followup_questions")
    
    return q


# === Get Summary ===
def structured_symptom_entry(user_id, symptom, followup_answer):
    if not user_id.strip() or not symptom.strip() or not followup_answer.strip():
        return "Error: User ID, symptom and followup required.", "", "", "", ""

    combined = f"""-Symptom: {symptom}
- Follow-up answers: {followup_answer}"""

    starting_sum = evaluate_with_openai(PROMPTS["summary_prompt"].format(combined=combined, symptom=symptom))
    followup_sum = evaluate_with_openai(PROMPTS["summary_followup"].format(combined=combined, symptom=symptom))
    tags = evaluate_with_openai(PROMPTS["summary_tags"].format(combined=combined, symptom=symptom))
    save_to_timeline(user_id, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "presenting complaint": starting_sum.strip(),
        "follow-up summary": followup_sum.strip(),
        "tags": tags.strip(),
    })
    return starting_sum, followup_sum, tags, "No Attachments", format_timeline(load_timeline(user_id))
# === Report Generation ===
def generate_report(user_id, reason, must_know, medz, prev_scan):
    if not user_id.strip() or not reason.strip():
        return None, "User ID and Reason are required."

    timeline = load_timeline(user_id)
    if not timeline:
        return None, "No entries found in timeline."

    #  Build timeline text to send to LLM
    timeline_entries = []
    for entry in timeline:
        if 'presenting complaint' in entry and 'follow-up summary' in entry:
            timeline_entries.append(
                f"{entry['time']} - {entry['presenting complaint']}\n{entry['follow-up summary']}"
            )
        elif 'follow-up summary' in entry:
            timeline_entries.append(
                f"{entry['time']} - {entry['follow-up summary']}"
            )

    full_text = "\n\n".join(timeline_entries)
    canonical_label, definition = retrieve_symptom_info(reason)

    if definition:
        preface = f"The patient presents with '{reason}', defined as: {definition}\n"
        filter_prompt = preface + PROMPTS["filter_prompt"].format(
            reason=reason,
            full_text=full_text, 
            must_know=must_know,
            medz=medz,
            prev_scan=prev_scan
        )
    else:
        filter_prompt = PROMPTS["filter_prompt"].format(
            reason=reason,
            full_text=full_text, 
            must_know=must_know,
            medz=medz,
            prev_scan=prev_scan
        )
    relevant_entries = evaluate_with_openai(filter_prompt, max_tokens=1000)

    if not relevant_entries or relevant_entries.strip() == "" or relevant_entries.lower().startswith("error"):
        return None, "AI report generation failed. Please check your prompt and try again."

    section_titles = [
        "Executive Summary",
        "Symptom Timeline",
        "Red Flags",
        "Emotional and Functional Impact",
        "Attachments"
    ]
    sections = {}
    split_pattern = f"""(?im)^\\s*({"|".join(re.escape(title) for title in section_titles)})\\s*[:\\-]?\\s*"""  
    parts = re.split(split_pattern, relevant_entries)

    if len(parts) > 1:
        content_parts = parts[1:]
        it = iter(content_parts)
        sections = dict(zip(it, it))
        normalized_sections = {}
        for title, content in sections.items():
            for canonical_title in section_titles:
                if canonical_title.lower() in title.lower():
                    normalized_sections[canonical_title] = content.strip()
                    break
        sections = normalized_sections

    for title in section_titles:
        if title not in sections:
            sections[title] = "No information available"

    for title, content in sections.items():
        sections[title] = content.replace('*', '')

    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("report_template.html")
    html_out = template.render(
        user_id=user_id,
        date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        sections=sections
    )

    pdf_filename = f"report_{user_id}.pdf"
    HTML(string=html_out).write_pdf(pdf_filename)

    return pdf_filename, "Report generated successfully."

# === Voice Recording JS ===
record_js = """
() => {
    return new Promise((resolve, reject) => {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert("Speech recognition not supported. Use Chrome or Edge.");
            resolve("");
            return;
        }
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            resolve(transcript);
        };
        recognition.onerror = function(event) {
            console.error("Speech recognition error:", event.error);
            resolve("Error: " + event.error);
        };
        recognition.start();
    });
}
"""

# === Gradio UI ===
with gr.Blocks(title="Sympli", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🩺 Sympli")
    with gr.Tabs():
        with gr.Tab("Log in"):
            user_id = gr.Textbox(label="🧑 User ID", placeholder="Enter ID")
            login_btn = gr.Button("🔄 Signup/Login")
            login_status = gr.Textbox(label="Status", interactive=False)
            login_btn.click(save_user_id_only, inputs=user_id, outputs=login_status)

        with gr.Tab("Medical Onboarding Questions"):
            name_input = gr.Textbox(label="Your Full Name")
            family_history = gr.Textbox(label="Family History")
            chronic_history = gr.Textbox(label="Past medical history")
            current_meds = gr.Textbox(label="Current Medications")
            past_investigations = gr.Textbox(label="Past Investigations")
            past_surgeries = gr.Textbox(label="Past Surgeries")
            allergies = gr.Textbox(label="Allergies")
            save_btn = gr.Button("SAVE")
            reset_btn = gr.Button("Reset Onboarding")
            save_status = gr.Textbox(label="Status", interactive=False)

            save_btn.click(
                save_onboarding_data,
                inputs=[user_id, name_input, family_history, chronic_history, current_meds, past_investigations, past_surgeries, allergies],
                outputs=[
                    save_status,
                    name_input, family_history, chronic_history,
                    current_meds, past_investigations, past_surgeries, allergies
                ]
            )

            reset_btn.click(
                reset_onboarding_fields,
                outputs=[
                    save_status,
                    name_input, family_history, chronic_history,
                    current_meds, past_investigations, past_surgeries, allergies
                ]
            )

            login_btn.click(
                auto_load_onboarding,
                inputs=user_id,
                outputs=[
                    save_status,
                    name_input, family_history, chronic_history,
                    current_meds, past_investigations, past_surgeries, allergies
                ]
            )

        with gr.Tab("My Timeline"):
            timeline_box = gr.Textbox(label="🧾 My Timeline", lines=40)
            login_btn.click(load_user_timeline, inputs=user_id, outputs=timeline_box)

        with gr.Tab("Record symptom"):
            gr.Markdown("### Step 1: Describe your symptom")
            with gr.Row():
                symptom_input = gr.Textbox(label="🗣️ Symptom")
                symptom_record_btn = gr.Button("🎤 Record your symptom")
                symptom_record_btn.click(fn=None, inputs=None, outputs=symptom_input, js=record_js)

        with gr.Tab("Follow-up"):
            gr.Markdown("### Step 2: Answer follow-up questions")
            ask_btn = gr.Button("Get Follow-up Questions")
            followup_q = gr.Textbox(label="🩺 Follow-up question", lines=10)
            q_btn = gr.Button("🎤 Record your answer")
            followup_answer = gr.Textbox(label="🩺 Your answer", lines=10)
            q_btn.click(fn=None, inputs=None, outputs=followup_answer, js=record_js)
            ask_btn.click(ask_followup, inputs=[user_id, symptom_input], outputs=followup_q)

        with gr.Tab("Get Summary"):
            submit_btn = gr.Button("🧠 Get Summary")
            summary = gr.Textbox(label="Presenting Complaint", lines=1)
            followup_sum = gr.Textbox(label="Follow-up Summary", lines=8)
            tags_summary = gr.Textbox(label = "Tags", lines = 1)
            attachments = gr.Textbox(label = "Attachments", lines = 1)
            submit_btn.click(structured_symptom_entry, inputs=[user_id, symptom_input, followup_answer], outputs=[summary, followup_sum, tags_summary , attachments ,timeline_box])

        with gr.Tab("PDF Report for Doctor Appointments"):
            gr.Markdown("## 🩺 Generate Doctor Report")
            reason_input = gr.Textbox(label="📌 Reason for appointment (required)")
            must_know_input = gr.Textbox(label="⚠️ Anything the doctor should understand?")
            meds_input = gr.Textbox(label="📌 Have you taken any medication for this problem? If yes, did it help?")
            test_input = gr.Textbox(label="⚠️ Have you has any tests/scans before for this problem? If yes, what were the results")
            report_btn = gr.Button("📄 Generate Report PDF")
            pdf_file = gr.File(label="📥 Download PDF")
            report_status = gr.Textbox(label="Status")
            report_btn.click(generate_report, inputs=[user_id, reason_input, must_know_input, meds_input, test_input], outputs=[pdf_file, report_status])

demo.launch()
 

    
