#!/usr/bin/env python3
"""
Device Configuration Management for Key Light Controller
Handles persistent storage of device labels and settings using XDG standards
"""

import json
import os
from typing import Dict, Optional
from pathlib import Path


class DeviceConfig:
    """Manages persistent device configuration using XDG Base Directory standard"""
    
    def __init__(self):
        self.config_path = self._get_config_path()
        self.config_data = self._load_config()
        
    def _get_config_path(self) -> Path:
        """Get configuration file path following XDG standards"""
        # Use XDG_CONFIG_HOME if set, otherwise default to ~/.config
        config_home = os.environ.get('XDG_CONFIG_HOME')
        if config_home:
            config_dir = Path(config_home) / 'keylight-control'
        else:
            config_dir = Path.home() / '.config' / 'keylight-control'
        
        # Create directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        return config_dir / 'device-labels.json'
    
    def _load_config(self) -> Dict:
        """Load configuration from file, return default if file doesn't exist"""
        default_config = {
            "version": "1.0",
            "devices": {}
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Validate config structure
                    if "version" in config and "devices" in config:
                        return config
                    else:
                        print(f"Warning: Invalid config structure in {self.config_path}, using defaults")
                        return default_config
            else:
                return default_config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Error loading config from {self.config_path}: {e}")
            return default_config
    
    def _save_config(self) -> bool:
        """Save configuration to file"""
        try:
            # Create a backup if file exists
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.json.backup')
                self.config_path.replace(backup_path)
            
            # Write new config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            # Set proper permissions (read/write for owner only)
            os.chmod(self.config_path, 0o600)
            return True
            
        except (IOError, OSError) as e:
            print(f"Error saving config to {self.config_path}: {e}")
            return False
    
    def get_label(self, mac_address: str, original_name: str) -> str:
        """Get custom label for device, return original name if no custom label exists"""
        if not mac_address:
            return original_name
            
        device_data = self.config_data.get('devices', {}).get(mac_address, {})
        return device_data.get('custom_label', original_name)
    
    def set_label(self, mac_address: str, original_name: str, custom_label: str, 
                  current_ip: str = None) -> bool:
        """Set custom label for device"""
        if not mac_address:
            print("Warning: Cannot set label - MAC address is required")
            return False
        
        # Initialize devices dict if it doesn't exist
        if 'devices' not in self.config_data:
            self.config_data['devices'] = {}
        
        # Update device information
        device_data = {
            'original_name': original_name,
            'custom_label': custom_label,
            'last_seen': self._get_timestamp()
        }
        
        if current_ip:
            device_data['last_ip'] = current_ip
        
        self.config_data['devices'][mac_address] = device_data
        
        return self._save_config()
    
    def remove_label(self, mac_address: str) -> bool:
        """Remove custom label for device (reset to default)"""
        if not mac_address:
            return False
        
        if mac_address in self.config_data.get('devices', {}):
            del self.config_data['devices'][mac_address]
            return self._save_config()
        
        return True  # Already removed/doesn't exist
    
    def has_custom_label(self, mac_address: str) -> bool:
        """Check if device has a custom label"""
        if not mac_address:
            return False
        
        device_data = self.config_data.get('devices', {}).get(mac_address, {})
        return 'custom_label' in device_data
    
    def get_all_devices(self) -> Dict[str, Dict]:
        """Get all configured devices"""
        return self.config_data.get('devices', {})
    
    def cleanup_old_devices(self, days: int = 30) -> int:
        """Remove device configs older than specified days, return count removed"""
        if days <= 0:
            return 0
        
        import time
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        devices = self.config_data.get('devices', {})
        to_remove = []
        
        for mac_address, device_data in devices.items():
            last_seen = device_data.get('last_seen', 0)
            if isinstance(last_seen, str):
                # Convert ISO timestamp to unix timestamp for comparison
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    last_seen = dt.timestamp()
                except (ValueError, AttributeError):
                    last_seen = 0
            
            if last_seen < cutoff_time:
                to_remove.append(mac_address)
        
        for mac_address in to_remove:
            del devices[mac_address]
        
        if to_remove:
            self._save_config()
        
        return len(to_remove)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def export_config(self, export_path: str) -> bool:
        """Export configuration to specified file"""
        try:
            export_file = Path(export_path)
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, OSError) as e:
            print(f"Error exporting config to {export_path}: {e}")
            return False
    
    def import_config(self, import_path: str, merge: bool = True) -> bool:
        """Import configuration from specified file"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                print(f"Import file does not exist: {import_path}")
                return False
            
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            if merge:
                # Merge with existing config
                imported_devices = imported_config.get('devices', {})
                self.config_data.setdefault('devices', {}).update(imported_devices)
            else:
                # Replace entire config
                self.config_data = imported_config
            
            return self._save_config()
            
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"Error importing config from {import_path}: {e}")
            return False