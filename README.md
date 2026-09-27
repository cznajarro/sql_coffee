# ☕ SQL Coffee
 
A coffee-shop idle/management mini-game built with **Python + Pygame** that doubles as a **data generator**: every customer, sale, and upgrade purchase is written to a **SQLite database** in real time, producing a clean dataset you can explore with SQL and visualize in a dashboard.
 
Play the game, export the data, and answer questions like: *"Do grinder upgrades actually pay for themselves?"*
 
---
 
## 🎮 Gameplay
 
Each in-game day lasts 60 seconds of real time (compressed from an 8-hour workday — 1 real second ≈ 8 game minutes). Customers arrive, queue up, order drinks, and pay. You earn a profit margin on every completed order and can reinvest it in upgrades between (and during) days.
 
### Products
 
| Product | Price | Unit Cost | Prep Time | Popularity |
|---|---|---|---|---|
| House Coffee | $3.00 | $0.70 | 2.0s | 40 |
| Cold Brew | $4.50 | $1.10 | 3.0s | 25 |
| Vanilla Latte | $5.25 | $1.60 | 5.0s | 25 |
| Matcha Latte | $5.75 | $1.90 | 6.0s | 10 |
 
Higher-priced drinks earn more per sale but tie up the counter longer — and every second a customer waits is a second the next customer waits too.
 
### Upgrades
 
| Upgrade | Effect | Base Cost | Max Level |
|---|---|---|---|
| **Better Grinder** (G) | −10% prep time per level | $20.00 × level | 5 |
| **Store Sign** (S) | −8% customer arrival interval per level | $25.00 × level | 5 |
 
- Upgrades are **cumulative across days** and persist with your cash balance.
- The grinder helps you *serve* faster; the sign helps you *attract* faster. Each one alone creates a bottleneck somewhere — the fun is in finding the balance.
### Controls
 
| Key / Input | Action |
|---|---|
| `G` or click the Grinder button | Buy Better Grinder upgrade |
| `S` or click the Sign button | Buy Store Sign upgrade |
| `F` | Toggle 2× fast-forward |
| `SPACE` | Start the next day (after a day ends) |
| `ESC` | Quit (day progress is saved) |
 
You start each new game with **$30.00** cash. Progress (cash + upgrade levels) carries over between days.
 
---
 
## 🗄️ The Data
 
Every run produces `data/coffee_shop.db`, a SQLite database with a normalized schema:
 
```
products            — menu items (price, unit cost, prep time)
game_days           — one row per day (customers, orders completed, ending cash)
transactions        — one row per completed sale
    ├─ day_id, product_id, game_minute (0–480, an 8-hour day)
    ├─ sale_price, unit_cost, wait_seconds
    └─ grinder_level, sign_level   ← context at time of sale
upgrade_purchases   — one row per upgrade bought (day, name, level, cost)
```
 
Because every transaction records the upgrade levels in effect when it happened, the data supports genuinely interesting SQL: profit by product per strategy, wait-time distributions, throughput per game hour, and upgrade ROI.
 
### Analysis notebook
 
[`analysis.ipynb`](analysis.ipynb) loads four exported CSV runs from `data/csv/` — **no upgrades**, **grinder only**, **sign only**, and **combined** (10 game days each, 799 transactions total) — and compares them with pandas + matplotlib. The dataset is included, so you can run the whole analysis without playing a minute of the game.
 
---
 
## 🚀 Getting Started
 
**Requirements:** Python 3.10+ and [Pygame](https://www.pygame.org/).
 
```bash
# 1. Clone the repo
git clone https://github.com/cznajarro/sql_coffee.git
cd sql_coffee
 
# 2. Install dependencies
pip install -r requirements.txt
 
# 3. Play — the SQLite database is created automatically on first launch
python game.py
 
# 4. (Optional) Explore the data
sqlite3 data/coffee_shop.db
```
 
> The database schema is created and migrated automatically on launch, so it's safe to upgrade an existing save.
 
Then open `analysis.ipynb` in Jupyter to explore the sample dataset, or point it at your own exported CSVs.
 
---
 
## 📁 Project Structure
 
```
sql_coffee/
├── game.py               # The game: loop, rendering, economy, SQLite logging
├── analysis.ipynb        # SQL/pandas/matplotlib analysis of four upgrade strategies
├── assets/               # Pixel-art product & upgrade icons
└── data/
    ├── coffee_shop.db    # Generated at runtime (not committed)
    └── csv/              # Exported runs used by the notebook
        ├── *.csv                     # no-upgrade baseline run
        ├── grinder_*.csv             # grinder-only strategy
        ├── sign_*.csv                # sign-only strategy
        └── combined_*.csv            # both upgrades
```
 
---
 
## 💡 Ideas for Your Own Analysis
 
- Which product has the best **profit per prep-second**?
- At what level does the grinder upgrade **pay for itself**?
- How does average **customer wait time** trend over a day as the queue builds?
- Does the sign actually increase revenue, or just queue congestion?
---
 
## 🛣️ Roadmap
 
- [ ] Wait-time patience: customers leave if the queue is too slow
- [ ] Staff hires as a third upgrade line
- [ ] One-command CSV export from the database
- [ ] An interactive dashboard (Streamlit or Plotly Dash) fed by `coffee_shop.db`
## 📄 License
 
MIT — see [LICENSE](LICENSE).
