import os
import sys
import subprocess
from datetime import datetime

# Prepend project root directory to path to allow resolving packages
PROJECT_ROOT = r"c:\Users\KIIT0001\Desktop\project\FinGuard"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings
settings.setup_logging()

# Setup stdout for Unicode support
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import DatabaseConnection
from services import AlertService, CaseService
from engines import CaseManager
from exceptions import ValidationException


def reinit_db():
    print("Re-initializing schema database...")
    schema_script = r"C:\Users\KIIT0001\.gemini\antigravity-ide\brain\734e55c7-fca3-43e9-a168-638d3a3edb61\scratch\run_schema.py"
    subprocess.run([sys.executable, schema_script], check=True)
    print("Database re-initialized successfully.\n")


def test_valid_transitions(manager: CaseManager, alert_id: int, db: DatabaseConnection):
    print("Testing: Valid state transitions workflow...")
    
    # 1. Create Case
    case = manager.create_case(alert_id=alert_id, priority="HIGH", notes="Initial auto-alert case creation")
    assert case.case_id is not None
    assert case.status == "OPEN"
    print(f"  [PASS] Case created successfully. Status: {case.status}")

    # 2. Transition OPEN -> UNDER_REVIEW
    manager.change_status(case.case_id, "UNDER_REVIEW")
    loaded = manager.case_service.case_repo.find_by_id(case.case_id)
    assert loaded.status == "UNDER_REVIEW"
    print(f"  [PASS] Transition OPEN -> UNDER_REVIEW successful.")

    # 3. Transition UNDER_REVIEW -> ESCALATED
    manager.change_status(case.case_id, "ESCALATED")
    loaded = manager.case_service.case_repo.find_by_id(case.case_id)
    assert loaded.status == "ESCALATED"
    print(f"  [PASS] Transition UNDER_REVIEW -> ESCALATED successful.")

    # 4. Transition ESCALATED -> RESOLVED
    manager.resolve_case(case.case_id, resolution="Confirmed identity via manual callbacks")
    loaded = manager.case_service.case_repo.find_by_id(case.case_id)
    assert loaded.status == "RESOLVED"
    assert loaded.resolution == "Confirmed identity via manual callbacks"
    print(f"  [PASS] Transition ESCALATED -> RESOLVED successful with resolution: '{loaded.resolution}'")

    # 5. Transition RESOLVED -> CLOSED
    manager.close_case(case.case_id)
    loaded = manager.case_service.case_repo.find_by_id(case.case_id)
    assert loaded.status == "CLOSED"
    print(f"  [PASS] Transition RESOLVED -> CLOSED successful.")


def test_invalid_transitions(manager: CaseManager, alert_id: int):
    print("\nTesting: Invalid state transitions enforcement...")
    
    # Create a fresh case
    case = manager.create_case(alert_id=alert_id, priority="MEDIUM", notes="Invalid transitions testing case")
    assert case.status == "OPEN"

    # Try OPEN -> ESCALATED directly (should fail)
    try:
        manager.change_status(case.case_id, "ESCALATED")
        raise AssertionError("Failed to prevent invalid transition: OPEN -> ESCALATED")
    except ValidationException as ve:
        print(f"  [PASS] Prevented invalid transition: {ve}")

    # Try OPEN -> CLOSED directly (should fail)
    try:
        manager.change_status(case.case_id, "CLOSED")
        raise AssertionError("Failed to prevent invalid transition: OPEN -> CLOSED")
    except ValidationException as ve:
        print(f"  [PASS] Prevented invalid transition: {ve}")

    # Transition OPEN -> UNDER_REVIEW
    manager.change_status(case.case_id, "UNDER_REVIEW")

    # Try UNDER_REVIEW -> CLOSED (should fail, must go through RESOLVED first)
    try:
        manager.change_status(case.case_id, "CLOSED")
        raise AssertionError("Failed to prevent invalid transition: UNDER_REVIEW -> CLOSED")
    except ValidationException as ve:
        print(f"  [PASS] Prevented invalid transition: {ve}")

    # Transition UNDER_REVIEW -> RESOLVED
    manager.resolve_case(case.case_id, resolution="Auto-approve whitelisted client")

    # Transition RESOLVED -> CLOSED
    manager.close_case(case.case_id)
    assert manager.case_service.case_repo.find_by_id(case.case_id).status == "CLOSED"

    # Try CLOSED -> OPEN (should fail, closed is terminal)
    try:
        manager.change_status(case.case_id, "OPEN")
        raise AssertionError("Failed to prevent invalid transition: CLOSED -> OPEN")
    except ValidationException as ve:
        print(f"  [PASS] Prevented invalid transition: {ve}")


def test_assignments_and_notes(manager: CaseManager, alert_id: int):
    print("\nTesting: Case assignment and analyst note additions...")

    # Create Case
    case = manager.create_case(alert_id=alert_id, priority="LOW", notes="Case notes and assignment verification")

    # Assign Case
    manager.assign_case(case.case_id, "Analyst Sarah")
    loaded = manager.case_service.case_repo.find_by_id(case.case_id)
    assert loaded.assigned_to == "Analyst Sarah"
    print(f"  [PASS] Case assigned successfully to '{loaded.assigned_to}'")

    # Add Analyst Note
    manager.add_analyst_note(case.case_id, "First analyst note - checking transactions log")
    manager.add_analyst_note(case.case_id, "Second analyst note - phone logs verify client identity")
    loaded = manager.case_service.case_repo.find_by_id(case.case_id)
    assert "First analyst note" in loaded.analyst_notes
    assert "Second analyst note" in loaded.analyst_notes
    assert "\n" in loaded.analyst_notes
    print("  [PASS] Analyst notes appended successfully.")

    # Add Remark
    manager.add_remark(case.case_id, "First remark - check with supervisor")
    loaded = manager.case_service.case_repo.find_by_id(case.case_id)
    assert loaded.remarks == "First remark - check with supervisor"
    print("  [PASS] Case remarks saved successfully.")

    # Verify history event triggers
    history = manager.get_case_history(case.case_id)
    # Events expected: CASE_CREATED, CASE_UPDATED (assignment), CASE_UPDATED (note 1), CASE_UPDATED (note 2), CASE_UPDATED (remark)
    assert len(history) == 5
    assert history[0].event_type == "CASE_CREATED"
    assert history[1].event_type == "CASE_UPDATED"
    print(f"  [PASS] Case events history retrieves correctly (Count: {len(history)}).")


def main():
    print("==================================================")
    print("        Case Management Verification Tests")
    print("==================================================\n")
    
    reinit_db()
    db = DatabaseConnection()
    
    alert_serv = AlertService()
    manager = CaseManager()

    # Generate sample Alert to link with cases
    # Alert status is OPEN, severity is MEDIUM
    alert = alert_serv.generate_alert(
        transaction_id=1,
        customer_id=1,
        risk_score=60,
        severity="MEDIUM",
        status="OPEN"
    )
    alert2 = alert_serv.generate_alert(
        transaction_id=2,
        customer_id=2,
        risk_score=70,
        severity="HIGH",
        status="OPEN"
    )
    alert3 = alert_serv.generate_alert(
        transaction_id=3,
        customer_id=3,
        risk_score=80,
        severity="CRITICAL",
        status="OPEN"
    )

    test_valid_transitions(manager, alert.alert_id, db)
    test_invalid_transitions(manager, alert2.alert_id)
    test_assignments_and_notes(manager, alert3.alert_id)
    
    print("\n==================================================")
    print("         All Case Management Tests Passed!")
    print("==================================================")


if __name__ == "__main__":
    main()
