import sys
import os
import unittest
import subprocess

# Prepend project root directory to path to allow resolving packages
PROJECT_ROOT = r"c:\Users\KIIT0001\Desktop\project\FinGuard"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_unittests():
    print("==================================================")
    print("      Executing FinGuard Model & Logic Unit Tests")
    print("==================================================")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add new unit and integration tests
    suite.addTests(loader.loadTestsFromName('test_unit_models'))
    suite.addTests(loader.loadTestsFromName('test_unit_risk_calculator'))
    suite.addTests(loader.loadTestsFromName('test_integration_flow'))
    suite.addTests(loader.loadTestsFromName('test_customer_validation'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()

def run_script_tests():
    print("\n==================================================")
    print("      Executing FinGuard Module Verification Scripts")
    print("==================================================")
    
    scripts = [
        "tests/test_alert_and_lists.py",
        "tests/test_analytics.py",
        "tests/test_case_management.py",
        "tests/test_investigation.py",
        "tests/test_reporting.py",
        "tests/test_risk_explanation.py",
        "tests/test_simulator.py"
    ]
    
    all_ok = True
    for s in scripts:
        script_path = os.path.join(PROJECT_ROOT, s.replace('/', os.sep))
        print(f"\n--> Running verification script: {s}...")
        try:
            res = subprocess.run([sys.executable, script_path], check=True, text=True, capture_output=False)
            print(f"SUCCESS: {s} executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"FAILED: {s} failed with exit code {e.returncode}.")
            all_ok = False
            
    return all_ok

def main():
    print("==================================================")
    print("      FinGuard Unified Test Suite Runner")
    print("==================================================\n")
    
    # 1. Re-initialize database
    print("Re-initializing schema database before tests...")
    schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
    try:
        subprocess.run([sys.executable, schema_script], check=True)
        print("Database schema loaded successfully.\n")
    except Exception as e:
        print(f"FATAL: Database reset failed: {e}")
        sys.exit(1)

    # 2. Run unit and integration tests
    unittests_ok = run_unittests()
    
    # 3. Run script-based tests
    scripts_ok = run_script_tests()
    
    print("\n==================================================")
    print("               TEST RUN REPORT SUMMARY")
    print("==================================================")
    print(f"Unit & Integration Tests Status: {'PASSED' if unittests_ok else 'FAILED'}")
    print(f"Verification Scripts Status:    {'PASSED' if scripts_ok else 'FAILED'}")
    print("==================================================")
    
    if unittests_ok and scripts_ok:
        print("\nALL TESTS PASSED SUCCESSFULLY!\n")
        sys.exit(0)
    else:
        print("\nTEST RUN ENCOUNTERED FAILURES.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
