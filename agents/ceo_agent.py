from llm import call_llm

from llm import call_llm
from message_bus import send_message
import json
import uuid
from datetime import datetime
import re


def decompose_idea(idea):
    prompt = f"""
    You are a startup CEO.

    Break this idea into tasks for:
    - product_agent
    - engineer_agent
    - marketing_agent
    - qa_agent

    Idea: {idea}

    critical rules - must be followed:
    - Output ONLY raw JSON.
    - Do NOT include markdown formatting.
    - Do NOT use ```json

    Output ONLY valid JSON:
    {{
        "product_agent": "...",
        "engineer_agent": "...",
        "marketing_agent": "...",
        "qa_agent": "..."
    }}
    """

    result = call_llm(prompt)


    try:
        # Remove ```json and ``` if present
        clean_result = re.sub(r"```json|```", "", result).strip()
        
        tasks = json.loads(clean_result)
    except Exception as e:
        print("❌ JSON parsing failed. Cleaned output:")
        print(clean_result)
        print("Error:", e)
        return

    print("\n✅ CEO created tasks:\n", tasks)

    # 🔥 SEND TASKS TO MESSAGE BUS
    for agent, task in tasks.items():
        msg = {
            "message_id": str(uuid.uuid4()),
            "from_agent": "ceo",
            "to_agent": agent,
            "message_type": "task",
            "payload": task,
            "timestamp": str(datetime.now()),
            "parent_message_id": None
        }

        send_message(msg)

    return tasks


def review_output(agent, output):
    pass


def send_revision(agent, feedback):
    pass