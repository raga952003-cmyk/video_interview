"""
Offline-only stub for populating `questions` from the web.

Do not run scrapers against sites whose terms forbid it. Prefer:
- Licensed datasets
- Manual curation (see backend/seed_db.py)
- Official APIs (e.g. GitHub API) with attribution

This file documents the intended pipeline; implement targets and parsing yourself.
"""

# Example shape for rows you would insert (matches backend seed_db.Row):
# {
#   "question_id": "uuid",
#   "role_category": "Python Developer",
#   "question_text": "...",
#   "scraped_ideal_answer": "...",
#   "source_url": "https://...",
# }

if __name__ == "__main__":
    print("Implement scraping offline, then INSERT into PostgreSQL or extend seed_db.py.")
