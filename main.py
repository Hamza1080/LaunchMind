from agents.ceo_agent import decompose_idea

idea = "AI travel planner for students with budget constraints"

decompose_idea(idea)

from message_bus import get_messages

print("\n📩 Messages for product_agent:")
print(get_messages("product_agent"))

