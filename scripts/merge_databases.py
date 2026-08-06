import json
import sqlite3
import re
import os
import glob
from datetime import datetime, timedelta

DB_PATH = "triagem_ait.db"

# Status mapping configuration for normalization
def normalize_status(status_str, obs_str):
    if not status_str:
        return "", obs_str
    
    status_clean = status_str.strip()
    status_upper = status_clean.upper()
    
    # Check for email/long text inside status
    if len(status_upper) > 100:
        if "DCT PROCESSAR" in status_upper:
            new_obs = f"[E-mail no campo Status]: {status_clean}"
            if obs_str:
                new_obs = f"{obs_str}\n{new_obs}"
            return "DCT PROCESSAR", new_obs
        else:
            return "DCT PROCESSAR", f"{obs_str}\n[Texto no campo Status]: {status_clean}" if obs_str else f"[Texto no campo Status]: {status_clean}"

    # Standard normalization patterns
    if "DCT" in status_upper and ("PROCESS" in status_upper or "PROCES" in status_upper or "PROCE" in status_upper or "POCESS" in status_upper or "POROCESS" in status_upper or "PROCESS" in status_upper or "PRCOESS" in status_upper or "PEOCESS" in status_upper or "PORCESS" in status_upper or "PRECESS" in status_upper or "PRTOCESS" in status_upper or "PRCOCESS" in status_upper or "PROCVESS" in status_upper or "PROVESS" in status_upper or "PROCERSS" in status_upper or "ROCESS" in status_upper):
        return "DCT PROCESSAR", obs_str
    if "DCTC" in status_upper or "DCCT" in status_upper:
        return "DCT PROCESSAR", obs_str
    if status_upper in ["PROCESSAR", "DCR PROCESSAR", "DCT PROCESSAR33", "DCT PROCESSAR", "DCT  - PROCESSAR", "DCT  -  PROCESSAR", "PROCESSAR", "J PROCESSADO AIT"]:
        return "DCT PROCESSAR", obs_str
    if "25786" in status_upper:
        return "DCT PROCESSAR", f"{obs_str}\n[ID no campo Status]: {status_clean}" if obs_str else f"[ID no campo Status]: {status_clean}"

    # CANCELADO variations
    if "CANCEL" in status_upper or "CANC" in status_upper or "CNCEL" in status_upper or "CASNCEL" in status_upper or "ANCELAS" in status_upper:
        m = re.search(r"SUBST(ITUID)?A?\s+AIT\s+(\d+)", status_upper)
        if m:
            ait_num = m.group(2)
            new_obs = f"Cancelado - Substituído pela AIT {ait_num}"
            if obs_str:
                new_obs = f"{obs_str}\n{new_obs}"
            return "CANCELADO", new_obs
        return "CANCELADO", obs_str
    
    # AIT SUBSTITUIDA variations
    if "SUBSTITU" in status_upper or "SUB AIT" in status_upper:
        return "AIT SUBSTITUIDA", obs_str
    
    # RENAINF variations
    if "RENAINF" in status_upper:
        return "RENAINF", obs_str

    return status_clean, obs_str

def parse_date(date_str):
    if not date_str:
        return None
    
    if "/Date(" in date_str:
        epoch_ms = int(re.search(r"-?\d+", date_str).group())
        dt = datetime(1970, 1, 1) + timedelta(milliseconds=epoch_ms)
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
            dt = datetime(year, dt.month, 28)
        return dt.strftime("%Y-%m-%d")
        
    try:
        if "T" in date_str:
            dt = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
        else:
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
                    
                    if part2 > 100:
                        year = part2
                        if part0 > 12:
                            day = part0
                            month = part1
                        else:
                            month = part0
                            day = part1
                    else:
                        year = part0
                        month = part1
                        day = part2
                
                if year == 3202: year = 2023
                if year == 202 or year == 222: year = 2022
                if year == 203 or year == 223: year = 2023
                if year == 224: year = 2024
                if year == 225: year = 2025
                if 190 <= year <= 260: year += 1800
                
                dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
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

def merge():
    print("Connecting to SQLite database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ait'")
    if not cursor.fetchone():
        print("Table 'ait' does not exist. Creating schema...")
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
        conn.commit()

    # Load existing IDs and AIT numbers
    cursor.execute("SELECT id, numero_ait FROM ait")
    seen_ids = set()
    seen_aits = set()
    
    for row in cursor.fetchall():
        db_id, db_ait = row
        if db_id is not None:
            seen_ids.add(db_id)
        if db_ait:
            seen_aits.add(str(db_ait).strip())
            
    print(f"Loaded {len(seen_ids)} existing IDs and {len(seen_aits)} unique AIT numbers from SQLite.")
    
    # Find all JSON exports in the folder
    json_files = glob.glob("TRIAGEM AIT*.json")
    if not json_files:
        print("No JSON export files found matching 'TRIAGEM AIT*.json'.")
        return
        
    print(f"Found {len(json_files)} JSON files to process:")
    for f in json_files:
        print(f"  - {f}")
        
    total_new_records_inserted = 0
    
    for json_file in json_files:
        print(f"\nProcessing {json_file}...")
        if not os.path.exists(json_file):
            print(f"File not found: {json_file}")
            continue
            
        with open(json_file, "r", encoding="utf-8-sig") as f:
            records = json.load(f)
            
        total_scanned = len(records)
        duplicate_id_skips = 0
        duplicate_ait_skips = 0
        inserted_count = 0
        
        for r in records:
            codigo = r.get("Codigo")
            data_val = parse_date(r.get("DataVal"))
            numero_ait = r.get("NumeroAIT")
            agente = r.get("Agente")
            raw_status = r.get("Status")
            raw_obs = r.get("Observacao")
            data_digitacao = parse_date(r.get("DataDigitacao"))
            placa = r.get("Placa")
            
            # 1. Clean Numero AIT
            clean_ait = ""
            if numero_ait is not None:
                clean_ait = str(numero_ait).strip()
                
            # 2. Duplicate Check by ID
            if codigo is not None:
                if codigo in seen_ids:
                    duplicate_id_skips += 1
                    continue
            
            # 3. Duplicate Check by AIT Number
            if clean_ait:
                if clean_ait in seen_aits:
                    duplicate_ait_skips += 1
                    continue
            
            # 4. Clean Placa
            if placa:
                placa = str(placa).strip().upper()
                
            # 5. Normalize Status and Observations
            status, obs = normalize_status(raw_status, raw_obs)
            
            try:
                cursor.execute("""
                INSERT INTO ait (id, data_ait, numero_ait, agente, status, observacao, data_digitacao, placa)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (codigo, data_val, clean_ait if clean_ait else None, agente, status, obs, data_digitacao, placa))
                
                # Add to sets to prevent duplication later in this file or other files
                if codigo is not None:
                    seen_ids.add(codigo)
                if clean_ait:
                    seen_aits.add(clean_ait)
                    
                inserted_count += 1
            except sqlite3.IntegrityError as ie:
                print(f"Integrity Error inserting ID {codigo}: {ie}")
                duplicate_id_skips += 1
                
        conn.commit()
        total_new_records_inserted += inserted_count
        
        print(f"Summary for {json_file}:")
        print(f"  - Scanned: {total_scanned}")
        print(f"  - Inserted: {inserted_count}")
        print(f"  - Skipped (Duplicate ID): {duplicate_id_skips}")
        print(f"  - Skipped (Duplicate AIT): {duplicate_ait_skips}")

    # Summary statistics after all files
    cursor.execute("SELECT COUNT(*), MIN(data_ait), MAX(data_ait) FROM ait")
    count, min_d, max_d = cursor.fetchone()
    print(f"\n========================================")
    print(f"Merge operation completed!")
    print(f"Total new records inserted: {total_new_records_inserted}")
    print(f"Total rows in SQLite database now: {count}")
    print(f"Min Infraction Date: {min_d}")
    print(f"Max Infraction Date: {max_d}")
    
    # Status count
    cursor.execute("SELECT status, COUNT(*) FROM ait GROUP BY status ORDER BY COUNT(*) DESC")
    print("\nStatus Distribution in Database:")
    for row in cursor.fetchall():
        print(f"  - {row[0] if row[0] else '[EMPTY]'}: {row[1]}")
        
    conn.close()

if __name__ == "__main__":
    merge()
