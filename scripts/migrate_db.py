import json
import sqlite3
import re
from datetime import datetime, timedelta

# Path to the exported JSON and the target SQLite database
JSON_PATH = "data_export.json"
DB_PATH = "triagem_ait.db"

# Status mapping configuration for normalization
def normalize_status(status_str, obs_str):
    if not status_str:
        return "", obs_str
    
    status_clean = status_str.strip()
    # Normalize unicode to avoid accents issues
    status_upper = status_clean.upper()
    
    # Check for email/long text inside status
    if len(status_upper) > 100:
        # If it contains "DCT PROCESSAR", save it as status and append the email to observation
        if "DCT PROCESSAR" in status_upper:
            new_obs = f"[E-mail no campo Status]: {status_clean}"
            if obs_str:
                new_obs = f"{obs_str}\n{new_obs}"
            return "DCT PROCESSAR", new_obs
        else:
            # Otherwise, keep as is or set a generic status
            return "DCT PROCESSAR", f"{obs_str}\n[Texto no campo Status]: {status_clean}" if obs_str else f"[Texto no campo Status]: {status_clean}"

    # Standard normalization patterns
    # 1. DCT PROCESSAR variations
    if "DCT" in status_upper and ("PROCESS" in status_upper or "PROCES" in status_upper or "PROCE" in status_upper or "POCESS" in status_upper or "POROCESS" in status_upper or "PROCESS" in status_upper or "PRCOESS" in status_upper or "PEOCESS" in status_upper or "PORCESS" in status_upper or "PRECESS" in status_upper or "PRTOCESS" in status_upper or "PRCOCESS" in status_upper or "PROCVESS" in status_upper or "PROVESS" in status_upper or "PROCERSS" in status_upper or "ROCESS" in status_upper):
        return "DCT PROCESSAR", obs_str
    if "DCTC" in status_upper or "DCCT" in status_upper:
        return "DCT PROCESSAR", obs_str
    if status_upper in ["PROCESSAR", "DCR PROCESSAR", "DCT PROCESSAR33", "DCT PROCESSAR", "DCT  - PROCESSAR", "DCT  -  PROCESSAR", "PROCESSAR", "J PROCESSADO AIT"]:
        return "DCT PROCESSAR", obs_str
    if "25786" in status_upper:  # Looks like an agent ID typed in status
        return "DCT PROCESSAR", f"{obs_str}\n[ID no campo Status]: {status_clean}" if obs_str else f"[ID no campo Status]: {status_clean}"

    # 2. CANCELADO variations
    if "CANCEL" in status_upper or "CANC" in status_upper or "CNCEL" in status_upper or "CASNCEL" in status_upper or "ANCELAS" in status_upper:
        # Check if it has substituted AIT info
        m = re.search(r"SUBST(ITUID)?A?\s+AIT\s+(\d+)", status_upper)
        if m:
            ait_num = m.group(2)
            new_obs = f"Cancelado - Substituído pela AIT {ait_num}"
            if obs_str:
                new_obs = f"{obs_str}\n{new_obs}"
            return "CANCELADO", new_obs
        return "CANCELADO", obs_str
    
    # 3. AIT SUBSTITUIDA variations
    if "SUBSTITU" in status_upper or "SUB AIT" in status_upper:
        return "AIT SUBSTITUIDA", obs_str
    
    # 4. RENAINF variations
    if "RENAINF" in status_upper:
        return "RENAINF", obs_str

    # Defaults for other cases
    return status_clean, obs_str

def parse_date(date_str):
    if not date_str:
        return None
    
    # PowerShell sometimes exports date as "\/Date(1693785600000)\/" or "\/Date(-2209161600000)\/"
    if "/Date(" in date_str:
        epoch_ms = int(re.search(r"-?\d+", date_str).group())
        dt = datetime(1970, 1, 1) + timedelta(milliseconds=epoch_ms)
        # Typo correction: year 3202 -> 2023, year 202 -> 2022
        year = dt.year
        if year == 3202: year = 2023
        if year == 202 or year == 222: year = 2022
        if year == 203 or year == 223: year = 2023
        if year == 224: year = 2024
        if year == 225: year = 2025
        if 190 <= year <= 260: year += 1800
        try:
            dt = dt.replace(year=year)
        except ValueError:
            # Handle leap year replacement failure if any
            dt = datetime(year, dt.month, 28)
        return dt.strftime("%Y-%m-%d")
        
    # Standard format parser
    # Access dates can be "04/09/2023 00:00:00" or ISO "2023-09-04T00:00:00"
    try:
        # Check ISO format
        if "T" in date_str:
            dt = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
        else:
            # Try MM/DD/YYYY or DD/MM/YYYY depending on locale
            parts = re.split(r'[-/ ]', date_str)
            if len(parts) >= 3:
                if len(parts[0]) == 4:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                else:
                    part0 = int(parts[0])
                    part1 = int(parts[1])
                    part2 = int(parts[2])
                    
                    if part2 > 100:  # part2 is Year
                        year = part2
                        if part0 > 12:  # part0 must be day
                            day = part0
                            month = part1
                        else:
                            # Access OLEDB standard is MM/DD/YYYY
                            month = part0
                            day = part1
                    else:
                        year = part0
                        month = part1
                        day = part2
                
                # Typo correction
                if year == 3202:
                    year = 2023
                if year == 202 or year == 222:
                    year = 2022
                if year == 203 or year == 223:
                    year = 2023
                if year == 224:
                    year = 2024
                if year == 225:
                    year = 2025
                if 190 <= year <= 260:
                    year += 1800
                
                dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Warning parsing date '{date_str}': {e}")
        m = re.findall(r"\d+", date_str)
        if len(m) >= 3:
            year = int(m[2]) if len(m[2]) == 4 else int(m[0])
            if year == 3202: year = 2023
            if year == 202 or year == 222: year = 2022
            if year == 203 or year == 223: year = 2023
            if year == 224: year = 2024
            if year == 225: year = 2025
            if 190 <= year <= 260: year += 1800
            return f"{year:04d}-{int(m[1]):02d}-{int(m[0]):02d}"
        return None

def migrate():
    print("Reading exported JSON file...")
    with open(JSON_PATH, "r", encoding="utf-8-sig") as f:
        records = json.load(f)
        
    print(f"Loaded {len(records)} records. Connecting to SQLite database '{DB_PATH}'...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing table if any
    cursor.execute("DROP TABLE IF EXISTS ait")
    
    # Create SQLite schema
    cursor.execute("""
    CREATE TABLE ait (
        id INTEGER PRIMARY KEY,
        data_ait TEXT,
        numero_ait TEXT,
        agente INTEGER,
        status TEXT,
        observacao TEXT,
        data_digitacao TEXT,
        placa TEXT
    )
    """)
    
    inserted_count = 0
    seen_ids = set()
    
    for r in records:
        codigo = r.get("Codigo")
        data_val = parse_date(r.get("DataVal"))
        numero_ait = r.get("NumeroAIT")
        agente = r.get("Agente")
        raw_status = r.get("Status")
        raw_obs = r.get("Observacao")
        data_digitacao = parse_date(r.get("DataDigitacao"))
        placa = r.get("Placa")
        
        # Check for duplicate ID or None
        if codigo is None:
            # Let SQLite generate a code or find next free
            print("Warning: found record with Null Codigo, skipping ID assignment")
        elif codigo in seen_ids:
            print(f"Warning: duplicate Codigo={codigo} found. Skipping this record to preserve integrity.")
            continue
        else:
            seen_ids.add(codigo)
            
        # Clean up placa
        if placa:
            placa = placa.strip().upper()
            
        # Clean up numero_ait
        if numero_ait:
            numero_ait = str(numero_ait).strip()
            
        # Normalize status and observations
        status, obs = normalize_status(raw_status, raw_obs)
        
        try:
            cursor.execute("""
            INSERT INTO ait (id, data_ait, numero_ait, agente, status, observacao, data_digitacao, placa)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (codigo, data_val, numero_ait, agente, status, obs, data_digitacao, placa))
            inserted_count += 1
        except sqlite3.IntegrityError as ie:
            print(f"Error inserting record ID {codigo}: {ie}")
            
        if inserted_count % 3000 == 0:
            print(f"Imported {inserted_count} records...")
            
    conn.commit()
    
    # Verify migration
    cursor.execute("SELECT COUNT(*), MIN(data_ait), MAX(data_ait) FROM ait")
    count, min_d, max_d = cursor.fetchone()
    print(f"\nMigration successfully completed!")
    print(f"Total Rows Imported: {count}")
    print(f"Min Infraction Date: {min_d}")
    print(f"Max Infraction Date: {max_d}")
    
    # Let's count standardized status
    cursor.execute("SELECT status, COUNT(*) FROM ait GROUP BY status ORDER BY COUNT(*) DESC")
    print("\nStandardized Status Distribution:")
    for row in cursor.fetchall():
        print(f"  - {row[0] if row[0] else '[EMPTY]'}: {row[1]}")
        
    conn.close()

if __name__ == "__main__":
    migrate()
