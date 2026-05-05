"""
Worker-side attack executor
Handles brute force attempts on assigned chunks
"""
import time
import threading
import os
from typing import Dict, Any, Optional
from netcluster.core.attacks.protocols import PROTOCOLS
from netcluster.utils.logger import setup_logger

logger = setup_logger(__name__)


class AttackExecutor:
    """
    Executes brute force attacks on worker node
    """
    
    def __init__(self, worker_id: str, send_result_callback, send_log_callback):
        self.worker_id = worker_id
        self.send_result = send_result_callback
        self.send_log = send_log_callback
        self.current_attack_id = None
        self.running = False
        self.paused = False
        self.stats = {
            'attempts': 0,
            'successes': 0,
            'start_time': None,
            'last_attempt_time': None
        }
    
    def execute_wordlist_attack(self, task_data: dict):
        """
        Execute attack using wordlist
        """
        self.current_attack_id = task_data.get('attack_id', 'unknown')
        self.current_task_id = task_data.get('_task_id', None)  # Store task_id for result sending
        self.running = True
        self.stats['start_time'] = time.time()
        self.stats['attempts'] = 0
        
        try:
            # Extract task data
            start_line = task_data['start_line']
            end_line = task_data['end_line']
            wordlist_file = task_data['wordlist_file']
            attack_type = task_data['attack_type']
            target = task_data['target']
            port = task_data.get('port')
            username = task_data.get('username')
            username_list = task_data.get('username_list')
            protocol_config = task_data.get('protocol_config', {})
            
            # Get protocol handler
            protocol_class = PROTOCOLS.get(attack_type)
            if not protocol_class:
                self.send_result({
                    'attack_id': self.current_attack_id,
                    'success': False,
                    'error': f'Unknown attack type: {attack_type}',
                    'attempts': 0
                })
                return
            
            # If username list provided, iterate through usernames
            if username_list and os.path.exists(username_list):
                self._execute_with_usernames(
                    protocol_class, target, port, username_list, 
                    wordlist_file, start_line, end_line, 
                    attack_type, protocol_config
                )
            else:
                # Single username mode
                self._execute_single_username(
                    protocol_class, target, port, username,
                    wordlist_file, start_line, end_line,
                    attack_type, protocol_config
                )
                
        except Exception as e:
            logger.error(f"Error executing wordlist attack: {e}")
            self.send_result({
                '_task_id': self.current_task_id,
                'attack_id': self.current_attack_id,
                'success': False,
                'error': str(e),
                'attempts': self.stats['attempts']
            })
        finally:
            self.running = False
    
    def _execute_single_username(self, protocol_class, target, port, username, 
                                 wordlist_file, start_line, end_line, 
                                 attack_type, protocol_config):
        """Execute attack with single username"""
        
        # Open wordlist and seek to start_line
        try:
            with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Skip to start line
                for _ in range(start_line):
                    f.readline()
                
                # Process passwords
                line_num = start_line
                for line in f:
                    if line_num >= end_line or not self.running:
                        break
                    
                    if self.paused:
                        time.sleep(0.1)
                        continue
                    
                    password = line.strip()
                    if not password:
                        line_num += 1
                        continue
                    
                    # Attempt authentication
                    self.stats['last_attempt_time'] = time.time()
                    
                    # Special handling for hash attacks
                    if attack_type == 'hash':
                        hash_value = target  # For hash, target is the hash
                        hash_type = protocol_config.get('hash_type', 'md5')
                        success, message = protocol_class.authenticate(
                            hash_value, password, hash_type=hash_type
                        )
                    elif attack_type == 'zip':
                        success, message = protocol_class.authenticate(
                            target, password, username=username
                        )
                    else:
                        success, message = protocol_class.authenticate(
                            target, username, password, port, **protocol_config
                        )
                    
                    self.stats['attempts'] += 1
                    
                    # Send progress update every 10 attempts
                    if self.stats['attempts'] % 10 == 0:
                        speed = self._calculate_speed()
                        self.send_log(f"Attempts: {self.stats['attempts']}, Speed: {speed:.1f}/s, Trying: {password[:20]}")
                    
                    if success:
                        # Password found!
                        self.send_result({
                            'attack_id': self.current_attack_id,
                            'success': True,
                            'username': username,
                            'password': password,
                            'attempts': self.stats['attempts'],
                            'message': message,
                            'worker_id': self.worker_id
                        })
                        self.running = False
                        break
                    
                    line_num += 1
            
            # If we get here, no password found in this chunk
            if self.running:
                self.send_result({
                    'attack_id': self.current_attack_id,
                    'success': False,
                    'attempts': self.stats['attempts'],
                    'worker_id': self.worker_id
                })
        
        except Exception as e:
            logger.error(f"Error in single username execution: {e}")
            self.send_result({
                'attack_id': self.current_attack_id,
                'success': False,
                'error': str(e),
                'attempts': self.stats['attempts']
            })
    
    def _execute_with_usernames(self, protocol_class, target, port, username_list,
                                wordlist_file, start_line, end_line,
                                attack_type, protocol_config):
        """Execute attack with multiple usernames"""
        try:
            # Load usernames
            with open(username_list, 'r', encoding='utf-8', errors='ignore') as f:
                usernames = [line.strip() for line in f if line.strip()]
            
            # Load passwords chunk
            passwords = []
            with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i < start_line:
                        continue
                    if i >= end_line:
                        break
                    if line.strip():
                        passwords.append(line.strip())
            
            # Try combinations
            total_combinations = len(usernames) * len(passwords)
            attempted = 0
            
            for username in usernames:
                if not self.running:
                    break
                
                for password in passwords:
                    if not self.running:
                        break
                    
                    if self.paused:
                        time.sleep(0.1)
                        continue
                    
                    # Attempt authentication
                    self.stats['last_attempt_time'] = time.time()
                    
                    if attack_type == 'hash':
                        hash_value = target
                        hash_type = protocol_config.get('hash_type', 'md5')
                        success, message = protocol_class.authenticate(
                            hash_value, password, hash_type=hash_type
                        )
                    else:
                        success, message = protocol_class.authenticate(
                            target, username, password, port, **protocol_config
                        )
                    
                    self.stats['attempts'] += 1
                    attempted += 1
                    
                    # Send progress update
                    if self.stats['attempts'] % 10 == 0:
                        speed = self._calculate_speed()
                        progress = (attempted / total_combinations) * 100
                        self.send_log(f"Progress: {progress:.1f}%, Speed: {speed:.1f}/s, Trying: {username}:{password[:10]}")
                    
                    if success:
                        # Credentials found!
                        self.send_result({
                            '_task_id': self.current_task_id,
                            'attack_id': self.current_attack_id,
                            'success': True,
                            'username': username,
                            'password': password,
                            'attempts': self.stats['attempts'],
                            'message': message,
                            'worker_id': self.worker_id
                        })
                        self.running = False
                        break
            
            # If we get here, no credentials found
            if self.running:
                self.send_result({
                    '_task_id': self.current_task_id,
                    'attack_id': self.current_attack_id,
                    'success': False,
                    'attempts': self.stats['attempts'],
                    'worker_id': self.worker_id
                })
        
        except Exception as e:
            logger.error(f"Error in multi-username execution: {e}")
            self.send_result({
                '_task_id': self.current_task_id,
                'attack_id': self.current_attack_id,
                'success': False,
                'error': str(e),
                'attempts': self.stats['attempts']
            })
    
    def execute_generation_attack(self, task_data: dict):
        """
        Execute attack using generated passwords (brute force)
        """
        self.current_attack_id = task_data.get('attack_id', 'unknown')
        self.current_task_id = task_data.get('_task_id', None)  # Store task_id for result sending
        self.running = True
        self.stats['start_time'] = time.time()
        self.stats['attempts'] = 0
        
        try:
            # Extract task data
            start_idx = task_data['start_idx']
            end_idx = task_data['end_idx']
            charset = task_data['charset']
            min_length = task_data['min_length']
            max_length = task_data['max_length']
            attack_type = task_data['attack_type']
            target = task_data['target']
            port = task_data.get('port')
            username = task_data.get('username')
            protocol_config = task_data.get('protocol_config', {})
            
            # Get protocol handler
            protocol_class = PROTOCOLS.get(attack_type)
            if not protocol_class:
                self.send_result({
                    'attack_id': self.current_attack_id,
                    'success': False,
                    'error': f'Unknown attack type: {attack_type}',
                    'attempts': 0
                })
                return
            
            # Generate and test passwords
            total_in_chunk = end_idx - start_idx + 1
            
            for idx in range(start_idx, end_idx + 1):
                if not self.running:
                    break
                
                if self.paused:
                    time.sleep(0.1)
                    continue
                
                # Generate password from index
                password = self._index_to_string(idx, charset, min_length, max_length)
                
                # Attempt authentication
                self.stats['last_attempt_time'] = time.time()
                
                if attack_type == 'hash':
                    hash_value = target
                    hash_type = protocol_config.get('hash_type', 'md5')
                    success, message = protocol_class.authenticate(
                        hash_value, password, hash_type=hash_type
                    )
                else:
                    success, message = protocol_class.authenticate(
                        target, username, password, port, **protocol_config
                    )
                
                self.stats['attempts'] += 1
                
                # Send progress update
                if self.stats['attempts'] % 10 == 0:
                    speed = self._calculate_speed()
                    progress = ((idx - start_idx + 1) / total_in_chunk) * 100
                    self.send_log(f"Progress: {progress:.1f}%, Speed: {speed:.1f}/s, Trying: {password}")
                
                if success:
                    # Password found!
                    self.send_result({
                        '_task_id': self.current_task_id,
                        'attack_id': self.current_attack_id,
                        'success': True,
                        'username': username,
                        'password': password,
                        'attempts': self.stats['attempts'],
                        'message': message,
                        'worker_id': self.worker_id
                    })
                    self.running = False
                    break
            
            # If we get here, no password found in this chunk
            if self.running:
                self.send_result({
                    '_task_id': self.current_task_id,
                    'attack_id': self.current_attack_id,
                    'success': False,
                    'attempts': self.stats['attempts'],
                    'worker_id': self.worker_id
                })
                
        except Exception as e:
            logger.error(f"Error executing generation attack: {e}")
            self.send_result({
                '_task_id': self.current_task_id,
                'attack_id': self.current_attack_id,
                'success': False,
                'error': str(e),
                'attempts': self.stats['attempts']
            })
        finally:
            self.running = False
    
    def _index_to_string(self, idx: int, charset: str, min_length: int, max_length: int) -> str:
        """Convert index to password string"""
        charset_size = len(charset)
        result = []
        
        # Find which length this index corresponds to
        current_idx = idx
        length = min_length
        
        for l in range(min_length, max_length + 1):
            combinations = charset_size ** l
            if current_idx < combinations:
                length = l
                break
            current_idx -= combinations
        
        # Generate password of determined length
        for _ in range(length):
            result.append(charset[current_idx % charset_size])
            current_idx //= charset_size
        
        return ''.join(result)
    
    def _calculate_speed(self) -> float:
        """Calculate attempts per second"""
        elapsed = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        if elapsed > 0:
            return self.stats['attempts'] / elapsed
        return 0
    
    def pause(self):
        """Pause execution"""
        self.paused = True
    
    def resume(self):
        """Resume execution"""
        self.paused = False
    
    def stop(self):
        """Stop execution"""
        self.running = False
