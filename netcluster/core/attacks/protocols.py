"""
Protocol handlers for different attack types
Each protocol knows how to authenticate against specific services
"""
import socket
import hashlib
import zipfile
import requests
from urllib.parse import urlparse
import base64
from typing import Tuple, Optional, Dict, Any
import time

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

try:
    import ftplib
    FTPLIB_AVAILABLE = True
except ImportError:
    FTPLIB_AVAILABLE = False

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


class AttackProtocol:
    """Base class for attack protocols"""
    
    @staticmethod
    def authenticate(target: str, username: str, password: str, port: int = None, **kwargs) -> Tuple[bool, str]:
        """
        Attempt authentication
        Returns: (success, message)
        """
        raise NotImplementedError


class SSHProtocol(AttackProtocol):
    """SSH brute force protocol"""
    
    @staticmethod
    def authenticate(host: str, username: str, password: str, port: int = 22, **kwargs) -> Tuple[bool, str]:
        if not PARAMIKO_AVAILABLE:
            return False, "paramiko library not available"
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, port=port, username=username, password=password, timeout=5)
            client.close()
            return True, "Authentication successful"
        except paramiko.AuthenticationException:
            return False, "Invalid credentials"
        except Exception as e:
            return False, f"Error: {str(e)}"


class FTPProtocol(AttackProtocol):
    """FTP brute force protocol"""
    
    @staticmethod
    def authenticate(host: str, username: str, password: str, port: int = 21, **kwargs) -> Tuple[bool, str]:
        if not FTPLIB_AVAILABLE:
            return False, "ftplib not available"
        
        try:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=5)
            ftp.login(username, password)
            ftp.quit()
            return True, "Authentication successful"
        except ftplib.error_perm:
            return False, "Invalid credentials"
        except Exception as e:
            return False, f"Error: {str(e)}"


class HTTPBasicProtocol(AttackProtocol):
    """HTTP Basic Authentication protocol"""
    
    @staticmethod
    def authenticate(url: str, username: str, password: str, port: int = 80, **kwargs) -> Tuple[bool, str]:
        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"http://{url}"
            
            # Add port if specified
            parsed = urlparse(url)
            if port and port not in [80, 443]:
                netloc = f"{parsed.hostname}:{port}"
                url = url.replace(parsed.netloc, netloc)
            
            # Create Basic Auth header
            auth = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers = {'Authorization': f'Basic {auth}'}
            
            response = requests.get(url, headers=headers, timeout=5, verify=False)
            
            if response.status_code == 200:
                return True, "Authentication successful"
            elif response.status_code == 401:
                return False, "Invalid credentials"
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, f"Error: {str(e)}"


class HTTPFormProtocol(AttackProtocol):
    """HTTP Form-based authentication protocol"""
    
    @staticmethod
    def authenticate(url: str, username: str, password: str, port: int = 80, form_data: Dict = None, **kwargs) -> Tuple[bool, str]:
        """
        Form-based authentication
        form_data should contain field names, e.g.:
        {'username_field': 'user', 'password_field': 'pass', 'action': '/login'}
        """
        try:
            if not form_data:
                # Default form fields
                form_data = {
                    'username_field': 'username',
                    'password_field': 'password',
                    'action': '/login',
                    'success_indicator': 'dashboard|welcome|success'
                }
            
            # Prepare form data
            data = {
                form_data.get('username_field', 'username'): username,
                form_data.get('password_field', 'password'): password
            }
            
            # Add any hidden fields
            if 'hidden_fields' in form_data:
                data.update(form_data['hidden_fields'])
            
            # Construct full URL
            if not url.startswith(('http://', 'https://')):
                url = f"http://{url}"
            
            # Append action path
            if form_data.get('action'):
                if not form_data['action'].startswith('/'):
                    form_data['action'] = '/' + form_data['action']
                target_url = url.rstrip('/') + form_data['action']
            else:
                target_url = url
            
            # Send POST request
            response = requests.post(target_url, data=data, timeout=5, 
                                   allow_redirects=True, verify=False)
            
            # Check for success indicators
            success_indicators = form_data.get('success_indicator', 'success|welcome').split('|')
            response_text = response.text.lower()
            
            for indicator in success_indicators:
                if indicator.lower() in response_text:
                    return True, "Authentication successful"
            
            # Check for failure indicators
            failure_indicators = form_data.get('failure_indicator', 'invalid|error|failed').split('|')
            for indicator in failure_indicators:
                if indicator.lower() in response_text:
                    return False, "Invalid credentials"
            
            # If no clear indicators, check response code
            if response.status_code == 200:
                return True, "Possible success (status 200)"
            else:
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            return False, f"Error: {str(e)}"


class HashProtocol(AttackProtocol):
    """Hash cracking protocol"""
    
    @staticmethod
    def authenticate(hash_value: str, password: str, hash_type: str = 'md5', **kwargs) -> Tuple[bool, str]:
        """Crack hash by comparing with generated hash"""
        try:
            password = password.strip()
            
            if hash_type.lower() == 'md5':
                computed = hashlib.md5(password.encode()).hexdigest()
            elif hash_type.lower() == 'sha1':
                computed = hashlib.sha1(password.encode()).hexdigest()
            elif hash_type.lower() == 'sha256':
                computed = hashlib.sha256(password.encode()).hexdigest()
            elif hash_type.lower() == 'sha512':
                computed = hashlib.sha512(password.encode()).hexdigest()
            else:
                return False, f"Unsupported hash type: {hash_type}"
            
            if computed.lower() == hash_value.lower():
                return True, f"Hash cracked: {password}"
            else:
                return False, "Hash mismatch"
        except Exception as e:
            return False, f"Error: {str(e)}"


class ZipProtocol(AttackProtocol):
    """ZIP file password cracking protocol"""
    
    @staticmethod
    def authenticate(filepath: str, password: str, username: str = None, **kwargs) -> Tuple[bool, str]:
        """Test ZIP file password"""
        try:
            with zipfile.ZipFile(filepath) as zf:
                # Try to extract a test file
                zf.setpassword(password.encode())
                # Test by reading the first file
                if zf.namelist():
                    zf.read(zf.namelist()[0])
                return True, "Password correct"
        except RuntimeError as e:
            if 'Bad password' in str(e):
                return False, "Invalid password"
            return False, f"Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"


class MySQLProtocol(AttackProtocol):
    """MySQL database authentication protocol"""
    
    @staticmethod
    def authenticate(host: str, username: str, password: str, port: int = 3306, database: str = None, **kwargs) -> Tuple[bool, str]:
        if not MYSQL_AVAILABLE:
            return False, "mysql.connector library not available"
        
        try:
            conn = mysql.connector.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                connection_timeout=5
            )
            conn.close()
            return True, "Authentication successful"
        except mysql.connector.Error as e:
            if e.errno == 1045:  # Access denied
                return False, "Invalid credentials"
            return False, f"Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"


# Protocol registry
PROTOCOLS = {
    'ssh': SSHProtocol,
    'ftp': FTPProtocol,
    'http_basic': HTTPBasicProtocol,
    'http_form': HTTPFormProtocol,
    'mysql': MySQLProtocol,
    'hash': HashProtocol,
    'zip': ZipProtocol,
}
