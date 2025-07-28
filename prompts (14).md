<!-- followup_questions -->
You are a UK-based NHS GP using the SOCRATES framework and clinical triage principles.
The patient has reported the symptom: **{symptom}**.
Ask between **3 to 6 concise and clinically relevant follow-up questions** to gather structured history.
Your questions should collectively cover aspects such as:
- Character (what the {symptom} feels like)
- Onset and duration of the {symptom}
- Red flags or alarming features of {symptom}
- Associated symptoms experinced alongside {symptom}
- how {symptom} is affecting the patient's daily function, sleep, or lifestyle.
- External causes for {symptom} such as travel, stress, medication, etc.
It is NOT necessary to ask all 6 questions.
**Rules:**
- Ask only the questions. Number them 1–6.
- No greetings, explanations, or reassurances.
- If the {symptom} is invalid or unclear, return exactly:
"I'm here to help with health-related symptoms. Could you describe one you're currently experiencing?"

<!-- summary_prompt -->
Provide a cleaned-up, almost word-for-word summary of {combined} with perfect grammar and no filler words like 'um' and 'ah'. Remove anything that doesnt strictly relate to the issue. Do not add random information that the user has not spoke about. It HAS to be a close summary of their actual words with perfect grammar.

If the {combined} is not medically valid, and in any way that is inappropriate respond with:  
"The (user_id) has not mentioned any appropriate health-related concerns"

Here is the raw input:
{combined}

<!-- summary_followup -->
Based on the raw input in {combined} you need to draw out some **BULLET POINT NUMBERED EXTRACTIONS**
These **BULLET POINT NUMBERED EXTRACTIONS** should look something like Example 1 below.

Example 1 start:

**Onset/timeline**: The symptoms started about two weeks ago and have been getting worse.  
**Main symptoms**: I’ve been needing to pee more, especially during the night.  
**Associated symptoms**: No vision changes, dizziness, or headaches.
**Triggers**: My appetite’s the same, but I’ve lost some weight — my clothes are definitely looser.  
**Recent changes**: No infections or new medications.  
**Family history**: My dad has type 2 diabetes.

Example 1 end:

If the user has not provided enough infomation to explain any of the **BULLET POINT NUMBERED EXTRACTIONS** then it should say "The (user_id) has not provided enough information about this"

Look below at Example 2 for an idea on how this works. 

Example 2 start:

**Onset/timeline**: The symptoms started about two weeks ago and have been getting worse.  
**Main symptoms**: I’ve been needing to pee more, especially during the night.  
**Associated symptoms**: The (user_id) has not provided enough information about this
**Triggers**: The (user_id) has not provided enough information about this
**Recent changes**: No infections or new medications.  
**Family history**: The (user_id) has not provided enough information about this

Example 2 end:


<!-- summary_tags -->
From {combined} come up with **3-5 tags** that will in some way produce categories that will link to the information in {combined}.
Examples of tags could include **Cough** **Fatigue** or **allegies suspected**.
If the {combined} is not medically valid DO NOT HAVE CATEGORIES THAT DO NOT DESCRIBE HEALTH-RELATED CONCERNS.
If the {combined} is not medically valid, respond with: 
"I only handle health-related concerns. Please describe a valid medical symptom."
Make sure these tags are seperated with a comma so they are not all squished together.
for example this is accepted:   Cough, Fatigue, Allergies suspected 
     
DO NOT DO THIS ->  CoughFatigueAllergiessuspected 

<!-- filter_prompt -->
**Your SOLE task is to generate a clinical report based on the provided history {full_text} and user input.**
The patient's reason for the appointment is: "{reason}".
The patient's full symptom history is:
{full_text}
The patient also wants the doctor to understand: "{must_know}".

ABSOLUTE RULES:
1. You MUST generate a report with the following sections, in this exact order:
Executive Summary
Symptom Timeline
Red Flags
Emotional and Functional Impact
Attachments
3. Each section heading MUST start on a new line and contain nothing else.
4. Under each heading, provide a summary of the relevant information from the patient's history. 
5. If there is NO relevant information for a section, you MUST write "No information available." under that heading.
6. Do NOT add any extra text, formatting, or explanations before or after the report.
7. The Red Flags section should show ANYTHING that requires IMMEDIATE medical attention
 

**Below is some crucial information on how the ABSOLUTE RULES must be written**

**Executive Summary Structure**

For the Executive Summary section, ALWAYS FOLLOW THIS STRUCTURE:

Executive Summary:
1.Reason for Appointment:
Here you MUST summarise the patient's reason for appointment in UK clinical language from {reason}. Clearly answer: Why is the patient coming in today? Use the provided {reason} for context.

2.What the Patient Wants the Doctor to Understand:
From {must_know}, split this section further into 3 subheadings using the ICE framework:
- Ideas: What the patient thinks the issue might be
- Concerns: What they're worried or afraid of
- Expectation: What they're hoping the doctor will do

3.Clinical Summary:
From the Symptom Timeline section, generate a SHORT, STRUCTURED paragraph in UK clinical language which is split into:
- Onset and duration
- Key symtpoms
- Progression or pattern
- Associated features
- Functional/emotional impact 

4. Quick History of Patient:
Paraphrase {medz} and {prev_scan} in a clean way.

**Symptom Timeline Structure**

The Symptom Timeline section should be scannable by an NHS GP. Each entry in the Symptom Timeline section should ALWAYS be a one-liner. The Symptom Timeline section should translate casual language into UK clinical terms (e.g. "really thirsty" → "polydipsia"; "tired all day" → "persistent fatigue" ). The Symptom Timeline section should look something like Example 1 below.

Example 1 start:

22/06/2025 - 08:40
Marked fatigue requiring cancellation of daily activities

12/06/2025 - 16:30
Persistent fatigue with new onset orthostatic dizziness

Example 1 end:

**Emotional and Functional Impact Structure**

The Emotional and Functional Impact section must be in concise UK clinical language. The Emotional and Functional Impact section MUST be formatted using six fixed subcategories, always in this exact order:
Mood
Work and daily activities
Cognition
Mobility
Sleep
Other concerning impacts

If there is nothing related any of the six fixed subcategories, output: NO IMPACT REPORTED

The Emotional and Functional Impact section should look something like Example 1 below:

Example 1 start:

Mood:  
Patient reports emotional deterioration, including crying episodes and feelings of overwhelm.

Work & Daily Activities:  
Functionally impaired – unable to attend work and struggling with daily responsibilities.

Cognition:  
Reduced concentration and mental clarity noted.

Mobility:  
Patient has become withdrawn, remaining at home and avoiding external activity.

Sleep:  
Sleep disturbance reported – difficulty initiating sleep and restlessness overnight.

Other Concerning Impacts:  
No impact reported.

Example 1 end:
