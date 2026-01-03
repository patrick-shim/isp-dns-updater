#!/usr/bin/env python3
"""
CloudFlare DNS Updater
Updates DNS A records for a domain with multiple WAN IPs
"""

import sys
import subprocess
import logging
import time
import os
import yaml
import requests
from pathlib import Path
from typing import Optional, List, Callable, Any, Dict
from functools import wraps


class Config:
    """Configuration management class"""
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        
        if config_path is None:
            script_dir = Path(__file__).parent
            config_path = script_dir / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"Please create config.yaml from config.example.yaml"
            )
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ValueError("Configuration file is empty")
            
            self._validate_config(config)
            return config
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def _validate_config(self, config: Dict) -> None:
        """Validate required configuration fields"""
        required_sections = ['cloudflare', 'dns', 'retry', 'timeouts', 'logging']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        required_fields = {
            'cloudflare': ['zone_id', 'api_token', 'api_base_url'],
            'dns': ['record_name', 'isp1_hostname', 'isp2_hostname', 'ttl', 'proxied'],
            'retry': ['max_retries', 'initial_delay', 'backoff_factor', 'dns_initial_delay'],
            'timeouts': ['api_timeout', 'dns_timeout'],
            'logging': ['level', 'format', 'date_format']
        }
        
        for section, fields in required_fields.items():
            for field in fields:
                if field not in config[section]:
                    raise ValueError(f"Missing required field '{field}' in section '{section}'")
    
    def get(self, section: str, key: str, default=None):
        """Get configuration value"""
        return self.config.get(section, {}).get(key, default)
    
    def get_section(self, section: str) -> Dict:
        """Get entire configuration section"""
        return self.config.get(section, {})


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (requests.RequestException,)
):
    """Decorator for retrying functions with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logging.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logging.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
            
            raise last_exception
        return wrapper
    return decorator


class CloudFlareDNSUpdater:
    def __init__(self, config: Config):
        self.config = config
        self.zone_id = config.get('cloudflare', 'zone_id')
        self.api_token = config.get('cloudflare', 'api_token')
        self.record_name = config.get('dns', 'record_name')
        self.base_url = config.get('cloudflare', 'api_base_url')
        self.max_retries = config.get('retry', 'max_retries')
        self.api_timeout = config.get('timeouts', 'api_timeout')
        self.dns_timeout = config.get('timeouts', 'dns_timeout')
        self.ttl = config.get('dns', 'ttl')
        self.proxied = config.get('dns', 'proxied')
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Initialized CloudFlare DNS Updater for {self.record_name}")
        self.logger.debug(f"Zone ID: {self.zone_id}, Max retries: {self.max_retries}")
    
    def get_ip_from_dns(self, hostname: str) -> Optional[str]:
        """Resolve hostname to IP using dig command with retry logic"""
        dns_initial_delay = self.config.get('retry', 'dns_initial_delay')
        backoff_factor = self.config.get('retry', 'backoff_factor')
        
        @retry_with_backoff(
            max_retries=self.max_retries,
            initial_delay=dns_initial_delay,
            backoff_factor=backoff_factor,
            exceptions=(subprocess.CalledProcessError, subprocess.TimeoutExpired)
        )
        def _resolve():
            self.logger.info(f"Resolving IP for hostname: {hostname}")
            
            result = subprocess.run(
                ["dig", "+short", hostname],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.dns_timeout
            )
            return result
        
        try:
            result = _resolve()
            ip = result.stdout.strip()
            
            if not ip:
                self.logger.error(f"No IP returned for {hostname}")
                return None
            
            if result.stderr:
                self.logger.warning(f"dig stderr for {hostname}: {result.stderr}")
            
            self.logger.info(f"Successfully resolved {hostname} to {ip}")
            return ip
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"DNS resolution timeout for {hostname}")
            raise
        except subprocess.CalledProcessError as e:
            self.logger.error(f"DNS resolution failed for {hostname}: {e}")
            if e.stderr:
                self.logger.error(f"Error output: {e.stderr}")
            raise
        except FileNotFoundError:
            self.logger.critical("'dig' command not found. Please install dnsutils/bind-tools package.")
            return None
        except Exception as e:
            self.logger.exception(f"Unexpected error resolving {hostname}: {e}")
            return None
    
    def get_existing_records(self) -> List[dict]:
        """Get all existing A records for the domain with retry logic"""
        initial_delay = self.config.get('retry', 'initial_delay')
        backoff_factor = self.config.get('retry', 'backoff_factor')
        
        @retry_with_backoff(
            max_retries=self.max_retries,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor
        )
        def _fetch_records():
            url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
            params = {
                "name": self.record_name,
                "type": "A"
            }
            
            self.logger.info(f"Fetching existing DNS records for {self.record_name}")
            
            response = requests.get(url, headers=self.headers, params=params, timeout=self.api_timeout)
            return response
        
        try:
            response = _fetch_records()
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                records = data.get("result", [])
                self.logger.info(f"Found {len(records)} existing record(s)")
                for record in records:
                    self.logger.debug(f"  - Record ID: {record.get('id')}, IP: {record.get('content')}")
                return records
            else:
                errors = data.get('errors', [])
                self.logger.error(f"CloudFlare API error getting records: {errors}")
                raise requests.RequestException(f"API returned errors: {errors}")
                
        except requests.Timeout:
            self.logger.error("Request timeout while fetching existing records")
            raise
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except requests.RequestException as e:
            self.logger.error(f"Request error fetching records: {e}")
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error fetching records: {e}")
            raise
    
    def delete_record(self, record_id: str, ip_content: str = "unknown") -> bool:
        """Delete a DNS record by ID with retry logic"""
        initial_delay = self.config.get('retry', 'initial_delay')
        backoff_factor = self.config.get('retry', 'backoff_factor')
        
        @retry_with_backoff(
            max_retries=self.max_retries,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor
        )
        def _delete():
            url = f"{self.base_url}/zones/{self.zone_id}/dns_records/{record_id}"
            
            self.logger.info(f"Deleting DNS record {record_id} (IP: {ip_content})")
            
            response = requests.delete(url, headers=self.headers, timeout=self.api_timeout)
            return response
        
        try:
            response = _delete()
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                self.logger.info(f"Successfully deleted record {record_id}")
                return True
            else:
                errors = data.get('errors', [])
                self.logger.error(f"CloudFlare API error deleting record {record_id}: {errors}")
                raise requests.RequestException(f"API returned errors: {errors}")
                
        except requests.Timeout:
            self.logger.error(f"Request timeout while deleting record {record_id}")
            raise
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error {e.response.status_code} deleting record {record_id}: {e.response.text}")
            raise
        except requests.RequestException as e:
            self.logger.error(f"Request error deleting record {record_id}: {e}")
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error deleting record {record_id}: {e}")
            raise
    
    def create_record(self, ip: str) -> bool:
        """Create a new A record with retry logic"""
        initial_delay = self.config.get('retry', 'initial_delay')
        backoff_factor = self.config.get('retry', 'backoff_factor')
        
        @retry_with_backoff(
            max_retries=self.max_retries,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor
        )
        def _create():
            url = f"{self.base_url}/zones/{self.zone_id}/dns_records"
            payload = {
                "type": "A",
                "name": self.record_name,
                "content": ip,
                "ttl": self.ttl,
                "proxied": self.proxied
            }
            
            self.logger.info(f"Creating DNS A record for {self.record_name} -> {ip} (TTL: {self.ttl}, Proxied: {self.proxied})")
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=self.api_timeout)
            return response
        
        try:
            response = _create()
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                record_id = data.get("result", {}).get("id", "unknown")
                self.logger.info(f"Successfully created record {record_id} for {ip}")
                return True
            else:
                errors = data.get('errors', [])
                self.logger.error(f"CloudFlare API error creating record for {ip}: {errors}")
                raise requests.RequestException(f"API returned errors: {errors}")
                
        except requests.Timeout:
            self.logger.error(f"Request timeout while creating record for {ip}")
            raise
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error {e.response.status_code} creating record for {ip}: {e.response.text}")
            raise
        except requests.RequestException as e:
            self.logger.error(f"Request error creating record for {ip}: {e}")
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error creating record for {ip}: {e}")
            raise
    
    def update_dns_records(self, ip1: str, ip2: str) -> bool:
        """Update DNS records with two IPs with comprehensive error handling"""
        self.logger.info("="*60)
        self.logger.info(f"Starting DNS update for {self.record_name}")
        self.logger.info(f"Target IPs: {ip1}, {ip2}")
        self.logger.info("="*60)
        
        try:
            self.logger.info("Phase 1: Cleaning old records")
            existing_records = self.get_existing_records()
            
            deleted_count = 0
            failed_deletes = []
            
            for record in existing_records:
                record_id = record.get("id")
                ip_content = record.get("content", "unknown")
                
                if record_id:
                    try:
                        if self.delete_record(record_id, ip_content):
                            deleted_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to delete record {record_id}: {e}")
                        failed_deletes.append(record_id)
            
            if failed_deletes:
                self.logger.warning(f"Failed to delete {len(failed_deletes)} record(s): {failed_deletes}")
            else:
                self.logger.info(f"Successfully deleted {deleted_count} old record(s)")
            
            self.logger.info("Phase 2: Creating new records")
            success1 = False
            success2 = False
            
            try:
                self.logger.info(f"Creating record for IP1: {ip1}")
                success1 = self.create_record(ip1)
            except Exception as e:
                self.logger.error(f"Failed to create record for {ip1}: {e}")
            
            try:
                self.logger.info(f"Creating record for IP2: {ip2}")
                success2 = self.create_record(ip2)
            except Exception as e:
                self.logger.error(f"Failed to create record for {ip2}: {e}")
            
            if success1 and success2:
                self.logger.info("="*60)
                self.logger.info(f"✓ SUCCESS: {self.record_name} now points to {ip1} and {ip2}")
                self.logger.info("="*60)
                return True
            elif success1 or success2:
                self.logger.warning("="*60)
                self.logger.warning(f"⚠ PARTIAL SUCCESS: Only {'IP1' if success1 else 'IP2'} was updated")
                self.logger.warning("="*60)
                return False
            else:
                self.logger.error("="*60)
                self.logger.error("✗ FAILURE: No records were created successfully")
                self.logger.error("="*60)
                return False
                
        except Exception as e:
            self.logger.exception(f"Critical error during DNS update: {e}")
            return False


def setup_logging(config: Config) -> None:
    """Configure logging with both console and optional file output"""
    log_level = config.get('logging', 'level', 'INFO')
    log_file = config.get('logging', 'log_file')
    log_format = config.get('logging', 'format')
    date_format = config.get('logging', 'date_format')
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        try:
            log_dir = Path(log_file).parent
            if not log_dir.exists():
                log_dir.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file))
        except Exception as e:
            print(f"Warning: Could not create log file {log_file}: {e}")
            print("Continuing with console logging only...")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )


def main():
    config_file = os.getenv('DNS_UPDATER_CONFIG', 'config.yaml')
    
    try:
        config = Config(config_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    logger.info("CloudFlare DNS Updater started")
    logger.info(f"Loaded configuration from: {config.config_path}")
    
    isp1_hostname = config.get('dns', 'isp1_hostname')
    isp2_hostname = config.get('dns', 'isp2_hostname')
    
    try:
        updater = CloudFlareDNSUpdater(config)
        
        logger.info(f"Resolving WAN IPs from {isp1_hostname} and {isp2_hostname}")
        
        ip1 = None
        ip2 = None
        
        try:
            ip1 = updater.get_ip_from_dns(isp1_hostname)
        except Exception as e:
            logger.error(f"Failed to resolve {isp1_hostname} after retries: {e}")
        
        try:
            ip2 = updater.get_ip_from_dns(isp2_hostname)
        except Exception as e:
            logger.error(f"Failed to resolve {isp2_hostname} after retries: {e}")
        
        if not ip1 or not ip2:
            logger.critical("Could not resolve one or both ISP IPs. Aborting.")
            logger.critical(f"IP1 ({isp1_hostname}): {ip1 or 'FAILED'}")
            logger.critical(f"IP2 ({isp2_hostname}): {ip2 or 'FAILED'}")
            sys.exit(1)
        
        success = updater.update_dns_records(ip1, ip2)
        
        if success:
            logger.info("DNS update completed successfully")
            sys.exit(0)
        else:
            logger.error("DNS update completed with errors")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
