#!/usr/bin/env python3
"""
Add Physician to Mobile Authentication Database

This script allows administrators to add new physicians to the
mobile_note.py authentication system.

Usage:
    python add_physician.py

Security Note:
    For production deployments, integrate with your hospital's
    LDAP/Active Directory for enterprise authentication.
"""

import sqlite3
import hashlib
import os
from datetime import datetime


def add_physician():
    """Interactive script to add a physician to the authentication database"""

    print("=" * 60)
    print("Grok Doc Mobile - Add Physician")
    print("=" * 60)
    print()

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Collect physician information
    physician_id = input("Physician ID (e.g., DR001): ").strip()
    if not physician_id:
        print("❌ Physician ID cannot be empty")
        return

    full_name = input("Full Name (e.g., Dr. Jane Smith): ").strip()
    if not full_name:
        print("❌ Full name cannot be empty")
        return

    npi_number = input("NPI Number (optional, press Enter to skip): ").strip()

    password = input("Password (min 8 characters): ").strip()
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return

    password_confirm = input("Confirm Password: ").strip()
    if password != password_confirm:
        print("❌ Passwords do not match")
        return

    # Hash the password
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    # Connect to database
    try:
        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()

        # Create table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS physicians
                     (physician_id TEXT PRIMARY KEY,
                      password_hash TEXT NOT NULL,
                      full_name TEXT NOT NULL,
                      npi_number TEXT,
                      last_login TIMESTAMP)''')

        # Check if physician already exists
        c.execute('SELECT physician_id FROM physicians WHERE physician_id = ?',
                  (physician_id,))
        if c.fetchone():
            print(f"❌ Physician ID '{physician_id}' already exists")
            conn.close()
            return

        # Insert new physician
        c.execute('''INSERT INTO physicians
                     (physician_id, password_hash, full_name, npi_number, last_login)
                     VALUES (?, ?, ?, ?, NULL)''',
                  (physician_id, password_hash, full_name, npi_number or None))

        conn.commit()
        conn.close()

        print()
        print("✅ Physician added successfully!")
        print()
        print("Credentials:")
        print(f"  Physician ID: {physician_id}")
        print(f"  Full Name: {full_name}")
        if npi_number:
            print(f"  NPI Number: {npi_number}")
        print()
        print("⚠️  IMPORTANT: Store these credentials securely!")
        print()

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def list_physicians():
    """List all physicians in the database"""

    if not os.path.exists('data/physician_auth.db'):
        print("No physicians found. Database does not exist yet.")
        return

    try:
        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()

        c.execute('''SELECT physician_id, full_name, npi_number, last_login
                     FROM physicians ORDER BY physician_id''')

        physicians = c.fetchall()
        conn.close()

        if not physicians:
            print("No physicians found in database.")
            return

        print()
        print("=" * 80)
        print(f"{'Physician ID':<15} {'Full Name':<30} {'NPI Number':<15} {'Last Login':<20}")
        print("=" * 80)

        for phys in physicians:
            physician_id, full_name, npi_number, last_login = phys
            npi_display = npi_number or "N/A"
            login_display = last_login[:19] if last_login else "Never"
            print(f"{physician_id:<15} {full_name:<30} {npi_display:<15} {login_display:<20}")

        print("=" * 80)
        print(f"Total physicians: {len(physicians)}")
        print()

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")


def delete_physician():
    """Delete a physician from the database"""

    if not os.path.exists('data/physician_auth.db'):
        print("No physicians found. Database does not exist yet.")
        return

    physician_id = input("Physician ID to delete: ").strip()
    if not physician_id:
        print("❌ Physician ID cannot be empty")
        return

    confirm = input(f"Are you sure you want to delete '{physician_id}'? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Deletion cancelled")
        return

    try:
        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()

        c.execute('DELETE FROM physicians WHERE physician_id = ?', (physician_id,))

        if c.rowcount > 0:
            conn.commit()
            print(f"✅ Physician '{physician_id}' deleted successfully")
        else:
            print(f"❌ Physician ID '{physician_id}' not found")

        conn.close()

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")


def main():
    """Main menu"""

    while True:
        print()
        print("Grok Doc Mobile - Physician Management")
        print("=" * 40)
        print("1. Add new physician")
        print("2. List all physicians")
        print("3. Delete physician")
        print("4. Exit")
        print()

        choice = input("Select option (1-4): ").strip()

        if choice == '1':
            add_physician()
        elif choice == '2':
            list_physicians()
        elif choice == '3':
            delete_physician()
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("❌ Invalid option. Please select 1-4.")


if __name__ == "__main__":
    main()
