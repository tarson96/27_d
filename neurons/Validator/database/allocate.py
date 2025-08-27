# The MIT License (MIT)
# Copyright © 2023 Rapiiidooo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import json
from typing import Tuple, Any

import bittensor as bt

from compute.utils.db import ComputeDb


def select_has_docker_miners_hotkey(db: ComputeDb):
    cursor = db.get_cursor()
    try:
        # Fetch all records from miner_details table
        cursor.execute("SELECT * FROM miner_details")
        rows = cursor.fetchall()

        hotkey_list = []
        for row in rows:
            if row[2]:
                details = json.loads(row[2])
                if details.get("has_docker", False) is True:
                    hotkey_list.append(row[1])
        return hotkey_list
    except Exception as e:
        bt.logging.error(f"Error while getting has_docker hotkeys from miner_details : {e}")
        return []
    finally:
        cursor.close()


# Fetch hotkeys from database that meets device_requirement
def select_allocate_miners_hotkey(db: ComputeDb, device_requirement):
    cursor = db.get_cursor()
    try:
        # Fetch all records from miner_details table
        cursor.execute("SELECT * FROM miner_details")
        rows = cursor.fetchall()

        # Check if the miner meets device_requirement
        hotkey_list = []
        for row in rows:
            details = json.loads(row[2])
            if allocate_check_if_miner_meet(details, device_requirement) is True:
                hotkey_list.append(row[1])
        return hotkey_list
    except Exception as e:
        bt.logging.error(f"Error while getting meet device_req. hotkeys from miner_details : {e}")
        return []
    finally:
        cursor.close()


#  Update the miner_details with specs
"""
This function is temporarily replaced by the hotfix.

def update_miner_details(db: ComputeDb, hotkey_list, benchmark_responses: Tuple[str, Any]):
    cursor = db.get_cursor()
    try:
        cursor.execute(f"DELETE FROM miner_details")
        for index, (hotkey, response) in enumerate(benchmark_responses):
            if json.dumps(response):
                cursor.execute("INSERT INTO miner_details (id, hotkey, details) VALUES (?, ?, ?)", (hotkey_list[index], hotkey, json.dumps(response)))
            else:
                cursor.execute("UPDATE miner SET unresponsive_count = unresponsive_count + 1 WHERE hotkey = ?", (hotkey))
                cursor.execute("DELETE FROM challenge_details WHERE uid IN (SELECT uid FROM miner WHERE unresponsive_count >= 10);")
        db.conn.commit()
    except Exception as e:
        db.conn.rollback()
        bt.logging.error(f"Error while updating miner_details : {e}")
    finally:
        cursor.close()
"""
#  Update the miner_details with specs
def update_miner_details(db: ComputeDb, hotkey_list, benchmark_responses: Tuple[str, Any]):
    """
    Update the miner_details table with the given benchmark responses.
    - Hotkeys present in Wandb are upserted with their details.
    - Hotkeys missing from Wandb are treated as failures.
    - After 2 consecutive failures, a miner is removed from the table.
    """
    cursor = db.get_cursor()
    try:
        # Retrieve existing hotkeys from the database
        cursor.execute("SELECT hotkey, no_specs_count FROM miner_details;")
        existing_rows = cursor.fetchall()
        existing_hotkeys = {hk for (hk, _cnt) in existing_rows}

        present_hotkeys = set(hotkey_list)

        # Update or insert details for present hotkeys
        for hotkey, response in benchmark_responses:
            if response:
                cursor.execute("""
                    INSERT INTO miner_details (hotkey, details, no_specs_count)
                    VALUES (?, ?, 0)
                    ON CONFLICT(hotkey) DO UPDATE SET
                        details = excluded.details,
                        no_specs_count = 0;
                """, (hotkey, json.dumps(response)))
            else:
                # Increment fail counter and remove after 2 fails
                cursor.execute("""
                    INSERT INTO miner_details (hotkey, details, no_specs_count)
                    VALUES (?, '{}', 1)
                    ON CONFLICT(hotkey) DO UPDATE SET
                        no_specs_count =
                            CASE
                                WHEN miner_details.no_specs_count >= 2 THEN 2
                                ELSE miner_details.no_specs_count + 1
                            END,
                        details =
                            CASE
                                WHEN miner_details.no_specs_count >= 2 THEN '{}'
                                ELSE excluded.details
                            END;
                """, (hotkey,))
                cursor.execute("""
                    DELETE FROM miner_details
                    WHERE hotkey = ? AND no_specs_count >= 2;
                """, (hotkey,))

        # Increment fail counters for missing hotkeys and remove after 2 fails
        missing_hotkeys = list(existing_hotkeys - present_hotkeys)
        for hk in missing_hotkeys:
            cursor.execute("""
                UPDATE miner_details
                SET no_specs_count = CASE
                    WHEN no_specs_count >= 2 THEN 2
                    ELSE no_specs_count + 1
                END
                WHERE hotkey = ?;
            """, (hk,))
            cursor.execute("""
                DELETE FROM miner_details
                WHERE hotkey = ? AND no_specs_count >= 2;
            """, (hk,))

        db.conn.commit()
    except Exception as e:
        db.conn.rollback()
        bt.logging.error(f"Error while updating miner_details: {e}")
    finally:
        cursor.close()


def get_miner_details(db):
    """
    Retrieves the specifications details for all miners from the database.

    :param db: An instance of ComputeDb to interact with the database.
    :return: A dictionary with hotkeys as keys and their details as values.
    """
    miner_specs_details = {}
    cursor = db.get_cursor()
    try:
        # Fetch all records from miner_details table
        cursor.execute("SELECT hotkey, details FROM miner_details")
        rows = cursor.fetchall()

        # Create a dictionary from the fetched rows
        for row in rows:
            hotkey = row[0]
            details = row[1]
            if details:  # If details are not empty, parse the JSON
                miner_specs_details[hotkey] = json.loads(details)
            else:  # If details are empty, set the value to an empty dictionary
                miner_specs_details[hotkey] = {}
    except Exception as e:
        bt.logging.error(f"Error while retrieving miner details: {e}")
    finally:
        cursor.close()

    return miner_specs_details


#  Update the allocation db
def update_allocation_db(hotkey: str, info: str, flag: bool):
    db = ComputeDb()
    cursor = db.get_cursor()
    try:
        if flag:
            # Insert or update the allocation details
            cursor.execute("""
                INSERT INTO allocation (hotkey, details)
                VALUES (?, ?) ON CONFLICT(hotkey) DO UPDATE SET
                details=excluded.details
            """, (hotkey, json.dumps(info)))
        else:
            # Remove the allocation details based on hotkey
            cursor.execute("DELETE FROM allocation WHERE hotkey = ?", (hotkey,))
        db.conn.commit()
    except Exception as e:
        db.conn.rollback()
        bt.logging.error(f"Error while updating allocation details: {e}")
    finally:
        cursor.close()
        db.close()

#  Update the ablacklist db
def update_blacklist_db(hotkeys: list, flag: bool):
    db = ComputeDb()
    cursor = db.get_cursor()
    try:
        if flag:
            # Insert the penalized hotkeys to the blacklist
            cursor.executemany("""
                INSERT INTO blacklist (hotkey)
                VALUES (?) ON CONFLICT(hotkey) DO NOTHING
            """, [(hotkey,) for hotkey in hotkeys])
        else:
            # Remove the hotkeys from the blacklist
            cursor.executemany("DELETE FROM blacklist WHERE hotkey = ?", [(hotkey,) for hotkey in hotkeys])
        db.conn.commit()
    except Exception as e:
        db.conn.rollback()
        bt.logging.error(f"Error while updating blacklist: {e}")
    finally:
        cursor.close()
        db.close()

# Check if the miner meets required details
def allocate_check_if_miner_meet(details, required_details):
    if not details:
        return False
    try:
        # CPU side
        cpu_miner = details["cpu"]
        required_cpu = required_details["cpu"]
        if required_cpu and (not cpu_miner or cpu_miner["count"] < required_cpu["count"]):
            return False

        # GPU side
        gpu_miner = details["gpu"]
        required_gpu = required_details["gpu"]
        if required_gpu:
            if not gpu_miner or gpu_miner["capacity"] <= required_gpu["capacity"] or gpu_miner["count"] < required_gpu["count"]:
                return False
            else:
                gpu_name = str(gpu_miner["details"][0]["name"]).lower()
                required_type = str(required_gpu["type"]).lower()
                if required_type not in gpu_name:
                    return False

        # Hard disk side
        hard_disk_miner = details["hard_disk"]
        required_hard_disk = required_details["hard_disk"]
        if required_hard_disk and (not hard_disk_miner or hard_disk_miner["free"] < required_hard_disk["capacity"]):
            return False

        # Ram side
        ram_miner = details["ram"]
        required_ram = required_details["ram"]
        if required_ram and (not ram_miner or ram_miner["available"] < required_ram["capacity"]):
            return False
    except Exception as e:
        bt.logging.error("The format is wrong, please check it again.")
        return False
    return True
