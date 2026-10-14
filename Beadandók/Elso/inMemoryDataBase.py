import re
import os
import pickle
import sys
import io

# Kényszerítjük a terminált az UTF-8 kódolásra (megoldja az ékezet problémát)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

# A memóriában tárolt adatbázis: Táblanevek -> Rekordok listája
database = {}
DB_FILE = "adatbazis.bin"

def load_database():
    """Adatbázis betöltése bináris fájlból induláskor."""
    global database
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as f:
            database = pickle.load(f)
        print(f"Adatbázis betöltve! Elérhető táblák: {list(database.keys())}")
    else:
        print("Új, üres adatbázis létrehozva.")

def save_database():
    """Adatbázis kimentése bináris fájlba."""
    with open(DB_FILE, "wb") as f:
        pickle.dump(database, f)
    print("Adatok sikeresen mentve a bináris fájlba!")

def execute_query(query):
    query = query.strip().strip(";")
    
    # --- 1. CREATE TABLE feldolgozása ---
    create_pattern = r"^CREATE\s+TABLE\s+(\w+)$"
    match_create = re.match(create_pattern, query, re.IGNORECASE)
    if match_create:
        table_name = match_create.group(1).lower()
        if table_name in database:
            print(f"Hiba: A '{table_name}' tábla már létezik!")
        else:
            database[table_name] = []
            print(f"Sikeres: '{table_name}' tábla létrehozva.")
        return

    # --- 2. INSERT INTO feldolgozása ---
    insert_pattern = r"^INSERT\s+INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)$"
    match_insert = re.match(insert_pattern, query, re.IGNORECASE)
    
    if match_insert:
        table_name, columns_str, values_str = match_insert.groups()
        table_name = table_name.lower()
        
        if table_name not in database:
            print(f"Hiba: A '{table_name}' tábla nem létezik!")
            return
            
        columns = [col.strip() for col in columns_str.split(",")]
        values = []
        for val in values_str.split(","):
            val = val.strip().strip("'").strip('"')
            if val.isdigit(): val = int(val)
            values.append(val)
            
        if len(columns) != len(values):
            print("Hiba: Az oszlopok és az értékek száma nem egyezik!")
            return
            
        new_record = dict(zip(columns, values))
        database[table_name].append(new_record)
        print(f"Sikeres beszúrás a '{table_name}' táblába: {new_record}")
        return

    # --- 3. SELECT feldolgozása ---
    # Minta: SELECT * FROM users WHERE nev LIKE '%Anna%' VAGY SELECT * FROM users WHERE id = 1
    select_pattern = r"^SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(\w+)\s*(=|LIKE)\s*(.*?))?$"
    match_select = re.match(select_pattern, query, re.IGNORECASE)
    
    if match_select:
        columns_str, table_name, where_col, operator, where_val = match_select.groups()
        table_name = table_name.lower()
        
        if table_name not in database:
            print(f"Hiba: A '{table_name}' tábla nem létezik!")
            return
            
        requested_cols = [col.strip() for col in columns_str.split(",")]
        
        # WHERE feltétel előkészítése
        if where_col:
            operator = operator.upper()
            where_val = where_val.strip().strip("'").strip('"')
            if where_val.isdigit() and operator == '=': 
                where_val = int(where_val)
        
        print(f"\n--- Eredmény ({table_name}) ---")
        talalat = 0
        for row in database[table_name]:
            # Szelekció (szűrés) alkalmazása
            if where_col:
                row_val = row.get(where_col)
                
                # Pontos egyezés (=)
                if operator == '=' and row_val != where_val:
                    continue
                    
                # Részleges egyezés (LIKE)
                elif operator == 'LIKE':
                    # Eltávolítjuk a % jeleket, és kisbetűssé alakítjuk a keresést
                    search_term = where_val.replace('%', '').lower()
                    if search_term not in str(row_val).lower():
                        continue
                
            talalat += 1
            # Projekció (oszlopok kiválasztása) alkalmazása
            if requested_cols == ["*"]:
                result = row
            else:
                result = {col: row.get(col) for col in requested_cols if col in row}
            print(result)
            
        if talalat == 0:
            print("Nincs a feltételnek megfelelő találat.")
        print("------------------------\n")
        return

    # --- 4. DELETE FROM feldolgozása ---
    # Minta: DELETE FROM users WHERE id = 1  VAGY csak DELETE FROM users
    delete_pattern = r"^DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(\w+)\s*=\s*(.*?))?$"
    match_delete = re.match(delete_pattern, query, re.IGNORECASE)
    
    if match_delete:
        table_name, where_col, where_val = match_delete.groups()
        table_name = table_name.lower()
        
        if table_name not in database:
            print(f"Hiba: A '{table_name}' tábla nem létezik!")
            return
            
        # Ha nincs WHERE feltétel, akkor mindent törlünk (biztonsági kérdéssel)
        if not where_col:
            biztos = input(f"Biztosan törölni akarod a(z) '{table_name}' tábla ÖSSZES rekordját? (i/n): ")
            if biztos.lower() == 'i':
                torolt_db = len(database[table_name])
                database[table_name] = []
                print(f"Sikeres: {torolt_db} rekord törölve. A tábla kiürült.")
            else:
                print("Törlés megszakítva.")
            return
            
        # WHERE feltétel feldolgozása
        where_val = where_val.strip().strip("'").strip('"')
        if where_val.isdigit(): 
            where_val = int(where_val)
            
        eredeti_hossz = len(database[table_name])
        
        # Csak azokat a rekordokat tartjuk meg, amik NEM egyeznek a törlési feltétellel
        database[table_name] = [
            row for row in database[table_name] 
            if row.get(where_col) != where_val
        ]
        
        torolt_db = eredeti_hossz - len(database[table_name])
        if torolt_db > 0:
            print(f"Sikeres: {torolt_db} rekord törölve a '{table_name}' táblából.")
        else:
            print("Nem található a feltételnek megfelelő rekord, így nem történt törlés.")
        return
    
    print("Hiba: Ismeretlen vagy hibás szintaxisú parancs!")

# --- Főprogram (REPL) ---
print("Kibővített In-Memory SQL Adatbázis")
load_database()

while True:
    try:
        user_input = input("SQL> ")
        if user_input.lower().strip() in ["exit", "quit"]:
            save_database()
            break
        elif user_input.strip():
            execute_query(user_input)
    except Exception as e:
        print(f"Váratlan hiba: {e}")