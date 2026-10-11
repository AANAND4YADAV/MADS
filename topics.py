from bins import CATEGORIES

ITEMS = ["a greasy pizza box", "a laminated wrapper box"]

TOPICS = [
    f"Which bin should {item} go in: {', '.join(CATEGORIES)}?"
    for item in ITEMS
]

DEFAULT_TOPIC = TOPICS[0]
