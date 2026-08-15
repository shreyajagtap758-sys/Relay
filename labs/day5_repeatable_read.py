"""
WEEK 0 DEBT — A2: Day 5 Bonus
==============================
Goal: REPEATABLE READ isolation level pe lost update automatically detect hota hai.
      PostgreSQL me ye hota hai, MySQL InnoDB me nahi.

Expected: "101" silently nahi aayega — ERROR: could not serialize access
due to concurrent update (SQLSTATE 40001) aayega.

Why: PostgreSQL REPEATABLE READ me lost updates detect karta hai aur
     serialization failure deke rollback kar deta hai. MySQL me ye nahi hota.
"""

import psycopg2
import threading
import time

def run_transaction(name: str, isolation_level: str):
    """
    Ek transaction chalata hai jo:
      1. counter table se current value read karta hai
      2. 0.5s wait karta hai (dusre transaction ko overlap karne ka time)
      3. value + 1 karke update karta hai

    Isolation level parameter se control hota hai.
    """
    conn = psycopg2.connect(
        host="localhost", port=5432, database="relay",
        user="postgres", password="relay"
    )
    # Auto-commit band — hum manually control karenge
    conn.autocommit = False

    try:
        cursor = conn.cursor()

        # Isolation level set karo — YE EXPERIMENT KA MAIN HISSA HAI
        cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")

        # Step 1: Read current value
        cursor.execute("SELECT value FROM counter WHERE id = 1")
        row = cursor.fetchone()
        current = row[0] if row else 0
        print(f"[{name}] Read value: {current}")

        # Step 2: Wait — dusra transaction overlap karega
        time.sleep(0.5)

        # Step 3: Increment and write
        new_val = current + 1
        cursor.execute("UPDATE counter SET value = %s WHERE id = 1", (new_val,))

        conn.commit()
        print(f"[{name}] COMMITTED with value: {new_val}")

    except Exception as e:
        conn.rollback()
        print(f"[{name}] ROLLED BACK: {type(e).__name__}: {e}")
    finally:
        conn.close()


def setup():
    """counter table banao aur initial value 100 daalo."""
    conn = psycopg2.connect(
        host="localhost", port=5432, database="relay",
        user="postgres", password="relay"
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS counter")
    cur.execute("CREATE TABLE counter (id int PRIMARY KEY, value int)")
    cur.execute("INSERT INTO counter VALUES (1, 100)")
    conn.close()
    print("Setup complete: counter = 100")


def experiment(isolation_level: str):
    """Do threads ek saath transaction chalate hain."""
    print(f"\n{'='*60}")
    print(f"ISOLATION LEVEL: {isolation_level}")
    print(f"{'='*60}")

    setup()

    t1 = threading.Thread(target=run_transaction, args=("T1", isolation_level))
    t2 = threading.Thread(target=run_transaction, args=("T2", isolation_level))

    t1.start()
    time.sleep(0.1)  # Thoda offset taaki overlap ho
    t2.start()

    t1.join()
    t2.join()

    # Final value check
    conn = psycopg2.connect(
        host="localhost", port=5432, database="relay",
        user="postgres", password="relay"
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT value FROM counter WHERE id = 1")
    final = cur.fetchone()[0]
    conn.close()

    print(f"\nFinal value: {final}")
    print(f"Expected: 102 (if both succeeded) OR 101 with error (if one failed)")

    if isolation_level == "READ COMMITTED" and final == 101:
        print("⚠️  LOST UPDATE CONFIRMED — Read Committed me silently galat!")
    elif isolation_level == "REPEATABLE READ" and final == 100:
        print("✅ REPEATABLE READ ne lost update detect kiya — 40001 error aaya!")


if __name__ == "__main__":
    # Pehle Read Committed se compare karo (Week 0 Day 5 ka original)
    experiment("READ COMMITTED")

    # Phir REPEATABLE READ — YE AAJ KA EXPERIMENT HAI
    experiment("REPEATABLE READ")