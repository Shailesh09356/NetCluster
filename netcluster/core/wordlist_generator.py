"""
Wordlist Generator - Safe string combination generator
"""
import itertools
import string
import time
from typing import Tuple
from netcluster.utils.logger import setup_logger
from netcluster.utils.config import MAX_WORDLIST_COMBINATIONS, WORDLIST_CHUNK_SIZE

logger = setup_logger(__name__)


def generate_wordlist(
    min_length: int,
    max_length: int,
    use_lower: bool = True,
    use_upper: bool = False,
    use_digits: bool = False,
    output_file: str = "wordlist.txt"
) -> Tuple[int, str, float]:
    """
    Generate wordlist file with character combinations
    
    Args:
        min_length: Minimum password length
        max_length: Maximum password length
        use_lower: Include lowercase letters
        use_upper: Include uppercase letters
        use_digits: Include digits
        output_file: Output file path
        
    Returns:
        Tuple of (total_generated, file_path, generation_time)
        
    Raises:
        ValueError: If invalid parameters or too many combinations
    """
    start_time = time.time()
    
    # Validate parameters
    if min_length < 1 or max_length < min_length:
        raise ValueError("Invalid length parameters")
    
    if not (use_lower or use_upper or use_digits):
        raise ValueError("At least one character set must be enabled")
    
    # Build character set
    charset = ""
    if use_lower:
        charset += string.ascii_lowercase
    if use_upper:
        charset += string.ascii_uppercase
    if use_digits:
        charset += string.digits
    
    # Estimate total combinations
    total_estimate = sum(len(charset) ** length for length in range(min_length, max_length + 1))
    
    if total_estimate > MAX_WORDLIST_COMBINATIONS:
        raise ValueError(f"Too many combinations ({total_estimate}). Maximum: {MAX_WORDLIST_COMBINATIONS}")
    
    logger.info(f"Generating wordlist: {min_length}-{max_length} chars, charset size: {len(charset)}, estimate: {total_estimate}")
    
    # Generate and write to file
    total_generated = 0
    chunk = []
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for length in range(min_length, max_length + 1):
                for combo in itertools.product(charset, repeat=length):
                    word = ''.join(combo)
                    chunk.append(word + '\n')
                    total_generated += 1
                    
                    # Write in chunks to avoid memory issues
                    if len(chunk) >= WORDLIST_CHUNK_SIZE:
                        f.writelines(chunk)
                        chunk = []
                    
                    # Safety check
                    if total_generated >= MAX_WORDLIST_COMBINATIONS:
                        logger.warning(f"Reached maximum combinations limit: {MAX_WORDLIST_COMBINATIONS}")
                        break
                
                if total_generated >= MAX_WORDLIST_COMBINATIONS:
                    break
            
            # Write remaining chunk
            if chunk:
                f.writelines(chunk)
    
    except Exception as e:
        logger.error(f"Error generating wordlist: {e}")
        raise
    
    generation_time = time.time() - start_time
    logger.info(f"Wordlist generated: {total_generated} entries in {generation_time:.2f}s -> {output_file}")
    
    return total_generated, output_file, generation_time
