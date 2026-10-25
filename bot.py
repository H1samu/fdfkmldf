name: Steam free games bot

on:
  schedule:
    - cron: "7,37 * * * *"
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: steam-bot
  cancel-in-progress: false

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install requests

      - name: Run bot
        env:
          BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
          CHANNEL_ID: ${{ secrets.CHANNEL_ID }}
        run: python bot.py

      - name: Save seen.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add seen.json
          git diff --cached --quiet || (git commit -m "Update seen.json" && git push)