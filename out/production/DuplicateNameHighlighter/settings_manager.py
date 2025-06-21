"""
Settings management for persistent configuration
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages application settings with JSON persistence"""
    
    def __init__(self, settings_file='settings.json'):
        self.settings_file = settings_file
        self.settings = {}
        self.default_settings = {
            'region': None,  # (x, y, width, height)
            'auto_scan': False,
            'scan_interval': 3,  # seconds
            'min_confidence': 30,  # OCR confidence threshold
            'hash_threshold': 5,  # Image change detection threshold
            'marker_colors': {
                'duplicate': [255, 165, 0, 180],  # Orange
                'multiple': [255, 0, 0, 180]      # Red
            },
            'window_geometry': {
                'x': 100,
                'y': 100,
                'width': 400,
                'height': 300
            },
            'ocr_config': {
                'language': 'eng',
                'psm': 6,  # Page segmentation mode
                'whitelist_chars': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '
            }
        }
        
        self.load_settings()
        logger.info("Settings manager initialized")
    
    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                logger.info(f"Settings loaded from {self.settings_file}")
            else:
                logger.info("No settings file found, using defaults")
                self.settings = {}
            
            # Merge with defaults for any missing keys
            for key, value in self.default_settings.items():
                if key not in self.settings:
                    self.settings[key] = value
                    
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            self.settings = self.default_settings.copy()
    
    def save_settings(self):
        """Save settings to JSON file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info(f"Settings saved to {self.settings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            return False
    
    def get_setting(self, key, default=None):
        """Get a setting value
        
        Args:
            key: Setting key (supports dot notation for nested keys)
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        try:
            # Handle dot notation for nested keys
            if '.' in key:
                keys = key.split('.')
                value = self.settings
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                return value
            else:
                return self.settings.get(key, default)
                
        except Exception as e:
            logger.error(f"Error getting setting '{key}': {str(e)}")
            return default
    
    def set_setting(self, key, value):
        """Set a setting value
        
        Args:
            key: Setting key (supports dot notation for nested keys)
            value: Value to set
        """
        try:
            # Handle dot notation for nested keys
            if '.' in key:
                keys = key.split('.')
                current = self.settings
                
                # Navigate to parent of target key
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                
                # Set the final key
                current[keys[-1]] = value
            else:
                self.settings[key] = value
                
            logger.debug(f"Setting '{key}' set to: {value}")
            
        except Exception as e:
            logger.error(f"Error setting '{key}': {str(e)}")
    
    def get_all_settings(self):
        """Get all settings
        
        Returns:
            Dictionary of all settings
        """
        return self.settings.copy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self.default_settings.copy()
        logger.info("Settings reset to defaults")
    
    def reset_setting(self, key):
        """Reset specific setting to default
        
        Args:
            key: Setting key to reset
        """
        if key in self.default_settings:
            self.settings[key] = self.default_settings[key]
            logger.info(f"Setting '{key}' reset to default")
        else:
            logger.warning(f"No default value for setting '{key}'")
    
    def validate_settings(self):
        """Validate current settings
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Validate region
            region = self.get_setting('region')
            if region is not None:
                if not isinstance(region, (list, tuple)) or len(region) != 4:
                    validation_results['errors'].append("Invalid region format")
                    validation_results['valid'] = False
                elif any(not isinstance(x, (int, float)) for x in region):
                    validation_results['errors'].append("Region coordinates must be numeric")
                    validation_results['valid'] = False
                elif region[2] <= 0 or region[3] <= 0:
                    validation_results['errors'].append("Region width and height must be positive")
                    validation_results['valid'] = False
            
            # Validate scan interval
            scan_interval = self.get_setting('scan_interval')
            if not isinstance(scan_interval, (int, float)) or scan_interval < 1:
                validation_results['errors'].append("Scan interval must be at least 1 second")
                validation_results['valid'] = False
            
            # Validate confidence threshold
            min_confidence = self.get_setting('min_confidence')
            if not isinstance(min_confidence, (int, float)) or not (0 <= min_confidence <= 100):
                validation_results['errors'].append("Confidence threshold must be between 0 and 100")
                validation_results['valid'] = False
            
        except Exception as e:
            validation_results['errors'].append(f"Validation error: {str(e)}")
            validation_results['valid'] = False
        
        return validation_results
    
    def export_settings(self, filename):
        """Export settings to file
        
        Args:
            filename: Output filename
            
        Returns:
            Boolean success status
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info(f"Settings exported to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting settings: {str(e)}")
            return False
    
    def import_settings(self, filename):
        """Import settings from file
        
        Args:
            filename: Input filename
            
        Returns:
            Boolean success status
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # Validate imported settings
            if not isinstance(imported_settings, dict):
                logger.error("Invalid settings format")
                return False
            
            # Merge with current settings
            self.settings.update(imported_settings)
            
            # Validate merged settings
            validation = self.validate_settings()
            if not validation['valid']:
                logger.warning(f"Imported settings validation warnings: {validation['warnings']}")
                if validation['errors']:
                    logger.error(f"Imported settings validation errors: {validation['errors']}")
                    return False
            
            logger.info(f"Settings imported from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing settings: {str(e)}")
            return False
