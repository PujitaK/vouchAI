import os, time
from pathlib import Path
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

client = Hindsight(
    base_url=os.environ["HINDSIGHT_BASE_URL"],
    api_key=os.environ["HINDSIGHT_API_KEY"],
    timeout=60.0,
)
BANK = "vouchai-smoke"

def timed(label, fn):
    start = time.time()
    result = fn()
    print(f"{label}: {time.time() - start:.1f}s")
    return result

try:
    client.create_bank(bank_id=BANK, name="VouchAI smoke test",
                       mission="I am a lending underwriter for AI agents. I track which agents repay and which default.")
except Exception as e:
    print("create_bank note:", e)

timed("retain", lambda: client.retain(
    bank_id=BANK,
    content="Agent scraper-07 under principal NovaOps defaulted on a 400 dollar data-scraping loan.",
    context="loan outcome",
    retain_async=False,
))

res = timed("recall", lambda: client.recall(bank_id=BANK, query="What do we know about NovaOps agents?"))
for r in res.results:
    print(" -", r.text)

ans = timed("reflect", lambda: client.reflect(
    bank_id=BANK,
    query="Should we lend 400 dollars to another NovaOps agent for data scraping?",
))
print(ans.text)
