from datetime import datetime, timedelta
import os
import subprocess
import random

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

days_back = 365
start_date = datetime.now() - timedelta(days=days_back)

for i in range(days_back + 1):
    current_date = start_date + timedelta(days=i)
    formatted_date = current_date.strftime("%Y-%m-%dT12:00:00")

    commits_today = random.randint(1, 30)

    env = os.environ.copy()
    env["GIT_COMMITTER_DATE"] = formatted_date
    env["GIT_AUTHOR_DATE"] = formatted_date

    for _ in range(commits_today):
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Refining code layout", "--quiet"],
            env=env,
            check=True
        )

    print(f"{GREEN}✔ Planted {commits_today} green squares for: {formatted_date.split('T')[0]}{RESET}")

print(f"{RED}🔥 All randomized commits staged! Push to GitHub now.{RESET}")