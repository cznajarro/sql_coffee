from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import random
import sqlite3

import pygame


WIDTH, HEIGHT = 1000, 650
FPS = 60
DAY_LENGTH_SECONDS = 90
STARTING_CASH = 25.00

COLORS = { #color palette for the game
    "cream": (247, 238, 220),
    "brown": (88, 57, 39),
    "dark_brown": (52, 35, 27),
    "green": (85, 125, 88),
    "gold": (220, 167, 74),
    "red": (184, 77, 69),
    "white": (255, 255, 255),
    "gray": (205, 196, 181),
}

DATA_DIR = Path(__file__).parent / "data" # directory for storing game data
DATABASE_PATH = DATA_DIR / "coffee_shop.db" # path to the SQLite database file


@dataclass(frozen=True) 
class Product: # represents a coffee product in the game
    name: str
    price: float
    cost: float
    prep_seconds: float
    popularity: int


@dataclass
class Order:
    product: Product
    remaining_seconds: float
    total_wait_seconds: float = 0.0


PRODUCTS = [ #list of the products in the game with name, price, cost to produce, preparation time, and popularity weight in that order
    Product("House Coffee", 3.00, 0.70, 2.0, 40),
    Product("Cold Brew", 4.50, 1.10, 3.0, 25),
    Product("Vanilla Latte", 5.25, 1.60, 5.0, 25),
    Product("Matcha Latte", 5.75, 1.90, 6.0, 10),
]


def create_database(): #creates the SQLite database and tables if they don't exist, and populates the products table with initial data
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript( #create the necessary tables
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL,
            unit_cost REAL NOT NULL,
            prep_seconds REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS game_days (
            day_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            customers_arrived INTEGER NOT NULL DEFAULT 0,
            orders_completed INTEGER NOT NULL DEFAULT 0,
            ending_cash REAL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            game_minute INTEGER NOT NULL,
            sale_price REAL NOT NULL,
            unit_cost REAL NOT NULL,
            wait_seconds REAL NOT NULL,
            FOREIGN KEY (day_id) REFERENCES game_days(day_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """
    )

    for product in PRODUCTS: #insert or update the products in the database
        connection.execute(
            """
            INSERT INTO products (name, price, unit_cost, prep_seconds)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                price = excluded.price,
                unit_cost = excluded.unit_cost,
                prep_seconds = excluded.prep_seconds
            """,
            (product.name, product.price, product.cost, product.prep_seconds),
        )

    connection.commit()
    return connection


def start_day(connection): #records the start of a new game day in the database and returns the day_id of the newly created record
    cursor = connection.execute(
        "INSERT INTO game_days (started_at) VALUES (?)",
        (datetime.now().isoformat(timespec="seconds"),),
    )
    connection.commit()
    return cursor.lastrowid


def finish_day(connection, day_id, customers, completed, cash): #updates the game_days table with the final statistics for the day, including the number of customers, completed orders, and ending cash balance
    connection.execute(
        """
        UPDATE game_days
        SET customers_arrived = ?, orders_completed = ?, ending_cash = ?
        WHERE day_id = ?
        """,
        (customers, completed, round(cash, 2), day_id),
    )
    connection.commit()


def record_sale(connection, day_id, order, game_minute): #records a completed sale in the transactions table, including the day_id, product_id, game minute, sale price, unit cost, and wait time for the order
    product_id = connection.execute(
        "SELECT product_id FROM products WHERE name = ?",
        (order.product.name,),
    ).fetchone()[0]

    connection.execute(
        """
        INSERT INTO transactions (
            day_id, product_id, game_minute, sale_price, unit_cost, wait_seconds
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            day_id,
            product_id,
            game_minute,
            order.product.price,
            order.product.cost,
            round(order.total_wait_seconds, 2),
        ),
    )
    connection.commit()


def choose_product(): #randomly picks a product from the PRODUCTS list based on their popularity weights and returns the selected product
    return random.choices(
        PRODUCTS,
        weights=[product.popularity for product in PRODUCTS],
        k=1,
    )[0]


def draw_text(surface, font, text, position, color=COLORS["dark_brown"]): #renders the specified text onto the given surface at the specified position using the provided font and color
    surface.blit(font.render(text, True, color), position)


def reset_game_day(connection, day_number, cash): #resets the game state for a new day, initializing the day_id, day_number, cash balance, elapsed time, next customer arrival time, and other relevant statistics
    return {
        "day_id": start_day(connection),
        "day_number": day_number,
        "cash": cash,
        "elapsed": 0.0,
        "next_customer": random.uniform(1.5, 3.5),
        "customers": 0,
        "completed": 0,
        "revenue": 0.0,
        "costs": 0.0,
        "queue": [],
        "recent_sales": [],
        "ended": False,
        "saved": False,
    }


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Bean Counter Cafe")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("arial", 30, bold=True)
    body_font = pygame.font.SysFont("arial", 20)
    small_font = pygame.font.SysFont("arial", 16)

    connection = create_database() #establish a connection to the SQLite database and create the necessary tables if they don't exist
    state = reset_game_day(connection, day_number=1, cash=STARTING_CASH) #initialize the game state for the first day with the starting cash balance
    running = True

    while running:
        dt = clock.tick(FPS) / 1000 #calculate the time elapsed since the last frame in seconds

        for event in pygame.event.get(): #handle user input events, such as quitting the game or pressing keys
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE and state["ended"]:
                    state = reset_game_day(
                        connection,
                        day_number=state["day_number"] + 1,
                        cash=state["cash"],
                    )

        if not state["ended"]: #update the game state if the day has not ended, including elapsed time, customer arrivals, order processing, and sales recording
            state["elapsed"] += dt
            state["next_customer"] -= dt

            if state["next_customer"] <= 0: #if it's time for a new customer to arrive, choose a product and add an order to the queue, then reset the next customer arrival time
                product = choose_product()
                state["queue"].append(Order(product, product.prep_seconds))
                state["customers"] += 1
                state["next_customer"] = random.uniform(1.5, 3.5)

            for order in state["queue"]:
                order.total_wait_seconds += dt

            if state["queue"]:# if there are orders in the queue, process the first order by decrementing its remaining preparation time and checking if it has been completed 
                current_order = state["queue"][0]
                current_order.remaining_seconds -= dt

                if current_order.remaining_seconds <= 0:
                    finished_order = state["queue"].pop(0)
                    profit = finished_order.product.price - finished_order.product.cost
                    state["cash"] += profit
                    state["revenue"] += finished_order.product.price
                    state["costs"] += finished_order.product.cost
                    state["completed"] += 1

                    game_minute = min(
                        480,
                        int((state["elapsed"] / DAY_LENGTH_SECONDS) * 480),
                    )
                    record_sale(connection, state["day_id"], finished_order, game_minute)

                    state["recent_sales"].insert(
                        0,
                        f"{finished_order.product.name}: +${profit:.2f}",
                    )
                    state["recent_sales"] = state["recent_sales"][:6]

            if state["elapsed"] >= DAY_LENGTH_SECONDS:
                state["ended"] = True

        if state["ended"] and not state["saved"]:
            finish_day(
                connection,
                state["day_id"],
                state["customers"],
                state["completed"],
                state["cash"],
            )
            state["saved"] = True

        screen.fill(COLORS["cream"]) #background

        pygame.draw.rect(screen, COLORS["brown"], (0, 0, WIDTH, 75)) #top bar
        draw_text(screen, title_font, "Coffee Cafe", (25, 20), COLORS["white"])
        draw_text(screen, body_font, f"Day {state['day_number']}", (580, 25), COLORS["white"])
        draw_text(screen, body_font, f"Cash: ${state['cash']:.2f}", (700, 25), COLORS["white"])
        draw_text(
            screen,
            body_font,
            f"Time: {max(0, DAY_LENGTH_SECONDS - state['elapsed']):.0f}s",
            (860, 25),
            COLORS["white"],
        )

        # Draw the main game area
        pygame.draw.rect(screen, COLORS["gray"], (40, 110, 590, 280), border_radius=12)
        pygame.draw.rect(screen, COLORS["dark_brown"], (40, 330, 590, 60), border_radius=8)
        draw_text(screen, title_font, "Front Counter", (220, 340), COLORS["white"])

        draw_text(screen, body_font, "Customer queue", (60, 125))
        if not state["queue"]:
            draw_text(screen, body_font, "Waiting for customers...", (60, 180), COLORS["brown"])

        for index, order in enumerate(state["queue"][:7]):
            x = 85 + index * 75
            y = 245
            pygame.draw.circle(screen, COLORS["green"], (x, y), 27)
            initials = "".join(word[0] for word in order.product.name.split())
            label = small_font.render(initials, True, COLORS["white"])
            screen.blit(label, label.get_rect(center=(x, y)))
            if index == 0:
                draw_text(
                    screen,
                    small_font,
                    f"Making: {order.product.name} ({max(0, order.remaining_seconds):.1f}s)",
                    (60, 290),
                )

        pygame.draw.rect(screen, COLORS["white"], (660, 110, 300, 280), border_radius=12)
        draw_text(screen, title_font, "Today's numbers", (680, 130))
        draw_text(screen, body_font, f"Customers: {state['customers']}", (680, 190))
        draw_text(screen, body_font, f"Orders completed: {state['completed']}", (680, 225))
        draw_text(screen, body_font, f"Revenue: ${state['revenue']:.2f}", (680, 260))
        draw_text(screen, body_font, f"Costs: ${state['costs']:.2f}", (680, 295))
        draw_text(
            screen,
            body_font,
            f"Profit: ${state['revenue'] - state['costs']:.2f}",
            (680, 330),
            COLORS["green"],
        )

        pygame.draw.rect(screen, COLORS["white"], (40, 420, 920, 190), border_radius=12)
        draw_text(screen, title_font, "Recent sales", (60, 440))
        for index, sale in enumerate(state["recent_sales"]):
            draw_text(screen, body_font, sale, (65, 485 + index * 23))

        if state["ended"]: #if the day has ended, display an overlay with the day's summary and prompt to start the next day
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((30, 20, 15, 185))
            screen.blit(overlay, (0, 0))
            summary = pygame.Rect(250, 170, 500, 300)
            pygame.draw.rect(screen, COLORS["cream"], summary, border_radius=16)
            draw_text(screen, title_font, f"Day {state['day_number']} complete", (350, 200))
            draw_text(screen, body_font, f"Revenue: ${state['revenue']:.2f}", (370, 270))
            draw_text(screen, body_font, f"Costs: ${state['costs']:.2f}", (370, 305))
            draw_text(
                screen,
                body_font,
                f"Profit: ${state['revenue'] - state['costs']:.2f}",
                (370, 340),
            )
            draw_text(screen, body_font, "Press SPACE to start the next day", (315, 405))

        pygame.display.flip()

    if not state["saved"]:
        # If the day is not saved, save the day's data to the database
        finish_day(
            connection,
            state["day_id"],
            state["customers"],
            state["completed"],
            state["cash"],
        )
    connection.close()
    pygame.quit()


if __name__ == "__main__":
    main()
