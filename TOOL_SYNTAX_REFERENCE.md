# Tool Syntax Reference Guide

## ⚠️ CRITICAL: Correct Tool Syntax

### Masscan
**CORRECT:**
```python
masscan(target='192.168.1.100', ports='80,443,8080', options='--rate 1000')
```

**IMPORTANT NOTES:**
- ✅ Masscan requires **IP address**, NOT domain names
- ✅ Use specific ports for speed: `'80,443,8080,22'`
- ⚠️ Full scan `'0-65535'` takes 10-30 minutes - avoid unless necessary
- ❌ Domain names will cause error: "unknown command-line parameter"

**Examples:**
- Single host, common ports: `masscan(target='192.168.1.100', ports='80,443,8080', options='--rate 1000')`
- Network scan: `masscan(target='192.168.1.0/24', ports='80,443,8080', options='--rate 1000')`

---

### Nmap
**CORRECT:**
```python
nmap(target='example.com', options='-sV -sC -p 80,443')
nmap(target='192.168.1.100', options='-sS -sV -O -p 22,80,443')
```

**IMPORTANT NOTES:**
- ✅ Nmap works with both IP addresses and domain names
- ✅ For quick scan: `-sV -sC -p [specific ports]`
- ⚠️ Avoid `-p-` (all ports) unless necessary - it takes 10-30 minutes
- ✅ Service detection: `-sV`
- ✅ OS detection: `-O`

**Examples:**
- Quick scan: `nmap(target='example.com', options='-sV -sC -p 80,443')`
- Standard scan: `nmap(target='192.168.1.100', options='-sS -sV -O')` (Top 1000 ports)
- Stealth scan: `nmap(target='192.168.1.100', options='-sS -sV -p 80,443')`

---

### Hydra
**CORRECT:**
```python
hydra(target='192.168.1.100', options='-L /root/data/wordlist/user.txt -P /root/data/wordlist/password.txt ssh')
```

**IMPORTANT NOTES:**
- ✅ Protocol (ssh/ftp/http) comes **AFTER** wordlist options
- ✅ Use `-L` for username list, `-P` for password list
- ❌ **WRONG**: `hydra(target='192.168.1.100', options='ssh -L users.txt -P passwords.txt')`
- ❌ **WRONG**: `hydra(target='ssh://192.168.1.100', ...)`

**Examples:**
- SSH: `hydra(target='192.168.1.100', options='-L /root/data/wordlist/user.txt -P /root/data/wordlist/password.txt ssh')`
- FTP: `hydra(target='192.168.1.100', options='-L /root/data/wordlist/user.txt -P /root/data/wordlist/password.txt ftp')`
- HTTP POST: `hydra(target='192.168.1.100', options='-L /root/data/wordlist/user.txt -P /root/data/wordlist/password.txt http-post-form "/login:user=^USER^&pass=^PASS^:F=incorrect"')`

---

### Nikto
**CORRECT:**
```python
nikto(target='https://example.com')
nikto(target='http://192.168.1.100')
```

**IMPORTANT NOTES:**
- ✅ Include protocol: `http://` or `https://`
- ✅ Works with both domain names and IP addresses
- ⚠️ Nikto scans can take 5-15 minutes

---

### Nuclei
**CORRECT:**
```python
nuclei(target='https://example.com', templates='cves,exposed-panels,vulnerabilities')
nuclei(target='https://example.com', templates='cves/2021/')
```

**IMPORTANT NOTES:**
- ✅ Include protocol: `http://` or `https://`
- ✅ Template categories: cves, exposed-panels, vulnerabilities, misconfigurations
- ✅ Fastest vulnerability scanner

---

### SQLMap
**CORRECT:**
```python
sqlmap(target='http://example.com/page.php?id=1', options='--dbs --batch')
sqlmap(target='http://example.com/login', options='--data="user=admin&pass=test" --dbs --batch')
```

**IMPORTANT NOTES:**
- ✅ Include full URL with parameters
- ✅ Use `--batch` for non-interactive mode
- ✅ For POST: use `--data="param1=value1&param2=value2"`

---

### Crackmapexec
**CORRECT:**
```python
crackmapexec('smb', '192.168.1.100', username='admin', password='password', options='--shares')
crackmapexec('smb', '192.168.1.0/24', username='admin', password='Password123')
```

**IMPORTANT NOTES:**
- ✅ First argument is protocol: smb, winrm, ssh, ldap, mssql
- ✅ Excellent for network-wide credential spraying

---

### Impacket
**CORRECT:**
```python
impacket('psexec.py', 'domain/user:pass@192.168.1.100')
impacket('secretsdump.py', 'admin:password@192.168.1.100')
impacket('GetNPUsers.py', 'domain.com/user -dc-ip 192.168.1.10')
```

**IMPORTANT NOTES:**
- ✅ Specify script name first: psexec.py, secretsdump.py, etc.
- ✅ Format: `domain/user:pass@target`

---

## Common Mistakes to Avoid

### ❌ Masscan with Domain Name
```python
# WRONG - masscan doesn't support domain names
masscan(target='example.com', ports='80,443', options='--rate 1000')

# CORRECT - use IP address
masscan(target='192.168.1.100', ports='80,443', options='--rate 1000')
```

### ❌ Hydra Protocol Before Wordlists
```python
# WRONG - protocol before wordlists
hydra(target='192.168.1.100', options='ssh -L users.txt -P passwords.txt')

# CORRECT - protocol after wordlists  
hydra(target='192.168.1.100', options='-L /root/data/wordlist/user.txt -P /root/data/wordlist/password.txt ssh')
```

### ❌ Full Port Scans Without Warning
```python
# SLOW - takes 10-30 minutes!
masscan(target='192.168.1.100', ports='0-65535', options='--rate 1000')
nmap(target='192.168.1.100', options='-p-')

# FAST - scan common ports first
masscan(target='192.168.1.100', ports='80,443,8080,22,21,25', options='--rate 1000')
nmap(target='192.168.1.100', options='-sV -p 80,443,22')
```

### ❌ Missing Protocols in URLs
```python
# WRONG - missing protocol
nikto(target='example.com')

# CORRECT - include protocol
nikto(target='https://example.com')
```

---

## Recommended Scan Workflow

### 1. Quick Network Discovery (Fast)
```python
# Scan common ports only - 1-2 minutes
masscan(target='192.168.1.0/24', ports='80,443,8080,22,21,25,3389', options='--rate 1000')
```

### 2. Detailed Service Detection (Medium Speed)
```python
# Once ports found, detailed scan - 2-5 minutes
nmap(target='192.168.1.100', options='-sV -sC -p 80,443,22')
```

### 3. Vulnerability Scanning (Fast)
```python
# Automated vulnerability detection - 5-10 minutes
nuclei(target='https://example.com', templates='cves,exposed-panels,vulnerabilities')
```

### 4. Standard Port Scan (Recommended)
```python
# Standard scan (Top 1000 ports) - 2-5 minutes
nmap(target='192.168.1.100', options='-sS -sV -O')
```
