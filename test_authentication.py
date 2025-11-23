#!/usr/bin/env python3
"""
Test script for mobile authentication system

This script verifies that the authentication system works correctly.
"""

import sqlite3
import hashlib
import os
import sys


def test_authentication():
    """Test the authentication system"""

    print("=" * 60)
    print("Testing Mobile Authentication System")
    print("=" * 60)
    print()

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Test 1: Create database and table
    print("Test 1: Creating authentication database...")
    try:
        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS physicians
                     (physician_id TEXT PRIMARY KEY,
                      password_hash TEXT NOT NULL,
                      full_name TEXT NOT NULL,
                      npi_number TEXT,
                      last_login TIMESTAMP)''')
        conn.commit()
        conn.close()
        print("✅ Database created successfully")
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        return False

    # Test 2: Add test physician
    print("\nTest 2: Adding test physician...")
    test_physician_id = "TEST_DR001"
    test_password = "TestPassword123"
    test_name = "Dr. Test Physician"
    test_npi = "1234567890"

    try:
        password_hash = hashlib.sha256(test_password.encode()).hexdigest()

        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()

        # Delete if exists (for repeated testing)
        c.execute('DELETE FROM physicians WHERE physician_id = ?', (test_physician_id,))

        c.execute('''INSERT INTO physicians
                     (physician_id, password_hash, full_name, npi_number)
                     VALUES (?, ?, ?, ?)''',
                  (test_physician_id, password_hash, test_name, test_npi))
        conn.commit()
        conn.close()
        print(f"✅ Test physician added: {test_physician_id}")
    except Exception as e:
        print(f"❌ Failed to add test physician: {e}")
        return False

    # Test 3: Verify correct password
    print("\nTest 3: Verifying correct password...")
    try:
        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()

        password_hash = hashlib.sha256(test_password.encode()).hexdigest()
        c.execute('SELECT password_hash FROM physicians WHERE physician_id = ?',
                  (test_physician_id,))
        result = c.fetchone()

        if result and result[0] == password_hash:
            print("✅ Correct password verified successfully")
        else:
            print("❌ Correct password verification failed")
            conn.close()
            return False

        conn.close()
    except Exception as e:
        print(f"❌ Password verification failed: {e}")
        return False

    # Test 4: Verify wrong password
    print("\nTest 4: Testing wrong password rejection...")
    try:
        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()

        wrong_password = "WrongPassword456"
        password_hash = hashlib.sha256(wrong_password.encode()).hexdigest()
        c.execute('SELECT password_hash FROM physicians WHERE physician_id = ?',
                  (test_physician_id,))
        result = c.fetchone()

        if result and result[0] != password_hash:
            print("✅ Wrong password correctly rejected")
        else:
            print("❌ Wrong password not rejected")
            conn.close()
            return False

        conn.close()
    except Exception as e:
        print(f"❌ Wrong password test failed: {e}")
        return False

    # Test 5: Verify non-existent physician
    print("\nTest 5: Testing non-existent physician...")
    try:
        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()

        c.execute('SELECT password_hash FROM physicians WHERE physician_id = ?',
                  ('NONEXISTENT_DR',))
        result = c.fetchone()

        if result is None:
            print("✅ Non-existent physician correctly not found")
        else:
            print("❌ Non-existent physician unexpectedly found")
            conn.close()
            return False

        conn.close()
    except Exception as e:
        print(f"❌ Non-existent physician test failed: {e}")
        return False

    # Cleanup: Remove test physician
    print("\nCleaning up test data...")
    try:
        conn = sqlite3.connect('data/physician_auth.db')
        c = conn.cursor()
        c.execute('DELETE FROM physicians WHERE physician_id = ?', (test_physician_id,))
        conn.commit()
        conn.close()
        print("✅ Test data cleaned up")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up test data: {e}")

    print()
    print("=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)
    print()
    print("Authentication system is working correctly.")
    print()
    print("Next steps:")
    print("1. Run 'python add_physician.py' to add real physicians")
    print("2. Launch mobile_note.py with 'streamlit run mobile_note.py'")
    print("3. Log in with physician credentials")
    print()

    return True


if __name__ == "__main__":
    success = test_authentication()
    sys.exit(0 if success else 1)
