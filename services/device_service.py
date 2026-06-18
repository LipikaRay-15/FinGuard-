import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import DatabaseConnection
from exceptions import (
    DeviceNotFoundException,
    DuplicateDeviceException,
    InvalidDeviceException,
    ValidationException
)
from models import Device
from repositories import DeviceRepository


class DeviceService:
    """
    Service class orchestrating business logic for Device profiling.
    Checks fingerprints, tracks IP changes, resolves OS details, and
    analyzes customer device transaction history.
    """
    def __init__(self) -> None:
        self.device_repo = DeviceRepository()
        self.db = DatabaseConnection()
        self.logger = logging.getLogger("finguard.services.device")

    def register_device(
        self,
        device_fingerprint: str,
        ip_address: str,
        operating_system: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Device:
        """
        Registers a new device or retrieves an existing one (updating its last seen).
        
        Raises:
            InvalidDeviceException: If format validations fail.
        """
        # Validate properties
        if not device_fingerprint or len(device_fingerprint) != 64:
            raise InvalidDeviceException("Device fingerprint must be a 64-character SHA-256 hash.")
        if not ip_address or ("." not in ip_address and ":" not in ip_address):
            raise InvalidDeviceException(f"Invalid IP address format: '{ip_address}'")

        # Search existing
        existing = self.device_repo.search({"device_fingerprint": device_fingerprint})
        if existing:
            dev = existing[0]
            dev.last_seen = datetime.now()
            self.device_repo.update(dev)
            self.logger.debug(f"Retrieved existing device {dev.device_id} and updated last_seen.")
            return dev

        try:
            dev = Device(
                device_id=None,
                device_fingerprint=device_fingerprint,
                ip_address=ip_address,
                operating_system=operating_system,
                user_agent=user_agent
            )
            created = self.device_repo.create(dev)
            self.logger.info(f"Registered new device ID {created.device_id}")
            from engines.event_manager import EventManager
            EventManager().log_event(
                event_type="DEVICE_REGISTERED",
                entity_type="DEVICE",
                entity_id=created.device_id,
                details={"fingerprint": created.device_fingerprint, "ip_address": created.ip_address}
            )
            return created
        except ValidationException as ve:
            raise InvalidDeviceException(f"Validation failure: {ve}")

    def update_last_seen(self, device_id: int) -> None:
        """
        Updates the device last_seen timestamp in database.
        
        Raises:
            DeviceNotFoundException: If device does not exist.
        """
        dev = self.device_repo.find_by_id(device_id)
        if not dev:
            raise DeviceNotFoundException(f"Device with ID {device_id} not found.")

        dev.last_seen = datetime.now()
        self.device_repo.update(dev)
        self.logger.debug(f"Updated last_seen for device {device_id}")

    def get_customer_devices(self, customer_id: int) -> List[Device]:
        """
        Queries and returns all unique devices used by a customer in prior transactions.
        """
        query = "SELECT DISTINCT device_id FROM transactions WHERE customer_id = %s AND device_id IS NOT NULL"
        rows = self.db.fetch_all(query, (customer_id,))
        
        devices = []
        for r in rows:
            dev_id = r["device_id"]
            dev = self.device_repo.find_by_id(dev_id)
            if dev:
                devices.append(dev)
        return devices

    def check_new_device(self, customer_id: int, device_fingerprint: str) -> bool:
        """
        Determines whether a device fingerprint is new for the specified customer.
        Returns True if the customer has never transacted using this device before.
        """
        existing = self.device_repo.search({"device_fingerprint": device_fingerprint})
        if not existing:
            return True # Fully unregistered device in our system

        dev = existing[0]
        # Check transaction logs
        query = "SELECT COUNT(*) AS tx_count FROM transactions WHERE customer_id = %s AND device_id = %s"
        row = self.db.fetch_one(query, (customer_id, dev.device_id))
        
        tx_count = row["tx_count"] if row else 0
        return tx_count == 0

    def track_ip_address(self, device_id: int, new_ip: str) -> None:
        """
        Monitors and logs IP address shifts for a specific device.
        
        Raises:
            DeviceNotFoundException: If device does not exist.
            InvalidDeviceException: If IP format is invalid.
        """
        if not new_ip or ("." not in new_ip and ":" not in new_ip):
            raise InvalidDeviceException(f"Invalid IP address format: '{new_ip}'")

        dev = self.device_repo.find_by_id(device_id)
        if not dev:
            raise DeviceNotFoundException(f"Device with ID {device_id} not found.")

        if dev.ip_address != new_ip:
            self.logger.info(f"IP address shift detected for device {device_id}: {dev.ip_address} -> {new_ip}")
            dev.ip_address = new_ip
            dev.last_seen = datetime.now()
            self.device_repo.update(dev)

    def track_device_os(self, device_id: int, new_os: str) -> None:
        """
        Updates operating system settings if changes occur.
        
        Raises:
            DeviceNotFoundException: If device does not exist.
        """
        dev = self.device_repo.find_by_id(device_id)
        if not dev:
            raise DeviceNotFoundException(f"Device with ID {device_id} not found.")

        if dev.operating_system != new_os:
            self.logger.info(f"OS updated for device {device_id}: {dev.operating_system} -> {new_os}")
            dev.operating_system = new_os
            dev.last_seen = datetime.now()
            self.device_repo.update(dev)

    def maintain_first_seen(self, device_id: int) -> datetime:
        """
        Retrieves the initial registration time of a device.
        
        Raises:
            DeviceNotFoundException: If device does not exist.
        """
        dev = self.device_repo.find_by_id(device_id)
        if not dev:
            raise DeviceNotFoundException(f"Device with ID {device_id} not found.")
        return dev.created_at

    def maintain_last_seen(self, device_id: int) -> datetime:
        """
        Updates and returns the last seen timestamp of a device.
        
        Raises:
            DeviceNotFoundException: If device does not exist.
        """
        dev = self.device_repo.find_by_id(device_id)
        if not dev:
            raise DeviceNotFoundException(f"Device with ID {device_id} not found.")

        dev.last_seen = datetime.now()
        self.device_repo.update(dev)
        return dev.last_seen
