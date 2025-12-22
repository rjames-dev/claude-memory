# Security Protocol - No Hardcoded Values

**Last Updated:** 2025-12-22
**Priority:** CRITICAL

---

## Core Rule: NEVER Hardcode Secrets or Environment-Specific Values

### ❌ What NOT to Do

```python
# BAD - Hardcoded password in fallback
password = os.getenv('PASSWORD', 'my_secret_password')

# BAD - Hardcoded port
DB_PORT = 5435

# BAD - Hardcoded URL
API_URL = 'http://localhost:3200'

# BAD - Hardcoded path
WORKSPACE = '/Users/john/workspace'
```

### ✅ What TO Do

```python
# GOOD - Required environment variable, fail if missing
password = os.getenv('CONTEXT_DB_PASSWORD')
if not password:
    raise ValueError("CONTEXT_DB_PASSWORD environment variable required")

# GOOD - Environment variable with safe default
port = int(os.getenv('POSTGRES_HOST_PORT', '5435'))

# GOOD - Environment variable for URLs
api_url = os.getenv('PROCESSOR_URL', 'http://localhost:3200')

# GOOD - Required path from environment
workspace = os.getenv('CLAUDE_WORKSPACE_ROOT')
if not workspace:
    raise ValueError("CLAUDE_WORKSPACE_ROOT must be set in .env file")
```

---

## Categories of Values

### 1. **Secrets** (NEVER have defaults)

**Definition:** Passwords, API keys, tokens, encryption keys

**Rule:** MUST fail if not provided

```python
# Passwords
db_password = os.getenv('CONTEXT_DB_PASSWORD')
if not db_password:
    raise ValueError("CONTEXT_DB_PASSWORD required - set in .env file")

# API Keys
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY required for this feature")
```

**Why:**
- Prevents accidental exposure
- Forces explicit configuration
- No false security from "convenient" defaults

---

### 2. **Environment-Specific Values** (Safe defaults OK)

**Definition:** Ports, URLs, timeouts, limits

**Rule:** Can have sensible defaults, must be overridable

```python
# Ports (default to standard values)
postgres_port = int(os.getenv('POSTGRES_HOST_PORT', '5435'))
processor_port = int(os.getenv('PROCESSOR_HOST_PORT', '3200'))

# URLs (default to standard service names)
ollama_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')

# Timeouts (default to reasonable values)
timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))

# Limits
row_limit_max = int(os.getenv('ROW_LIMIT_MAX', '1000000'))
```

**Why:**
- Convenience for standard setups
- Flexibility for custom deployments
- Documented in .env.example

---

### 3. **Paths** (Depends on use case)

**User-specific paths:** Must be provided
```python
# REQUIRED - varies per user
workspace_root = os.getenv('CLAUDE_WORKSPACE_ROOT')
if not workspace_root:
    raise ValueError("Set CLAUDE_WORKSPACE_ROOT in .env")
```

**Container paths:** Can have defaults
```python
# Container-internal path (Docker mount point)
workspace_mount = os.getenv('WORKSPACE_MOUNT', '/claude-workspace')
```

---

## Pre-Commit Checklist

Before committing ANY code, verify:

```markdown
Environment Variable Checklist:
□ No hardcoded passwords (search for 'password.*=.*["\']')
□ No hardcoded API keys (search for 'api.*key.*=.*["\']')
□ No hardcoded database credentials
□ Ports/URLs use environment variables
□ User-specific paths require env vars (fail if missing)
□ All env vars documented in .env.example
□ .env file is gitignored (never commit)
□ Test with missing env vars to ensure proper error messages
```

---

## Automated Checks

### 1. Pre-Commit Hook (Recommended)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Check for common hardcoding patterns

echo "Checking for hardcoded secrets..."

# Check for hardcoded passwords (excluding comments and docs)
if git diff --cached --name-only | grep -E '\.(py|js|ts)$' | xargs grep -l "password.*=.*['\"][^'\"]*['\"]" | grep -v test | grep -v example; then
    echo "❌ Potential hardcoded password found!"
    echo "Use os.getenv('PASSWORD') without fallback defaults for secrets"
    exit 1
fi

# Check for hardcoded API keys
if git diff --cached --name-only | grep -E '\.(py|js|ts)$' | xargs grep -l "api.*key.*=.*['\"]sk-" 2>/dev/null; then
    echo "❌ Potential hardcoded API key found!"
    exit 1
fi

# Check if .env files are being committed
if git diff --cached --name-only | grep -E '^\.env$'; then
    echo "❌ Attempting to commit .env file!"
    echo ".env files contain secrets and must not be committed"
    exit 1
fi

echo "✅ No hardcoded secrets detected"
```

### 2. Search Commands

```bash
# Find potential hardcoded passwords
grep -r "password.*=.*['\"]" --include="*.py" --include="*.js" . | grep -v ".env.example" | grep -v test

# Find potential API keys
grep -r "sk-ant-" --include="*.py" --include="*.js" .

# Find hardcoded ports outside config
grep -r "3200\|5435\|11434" --include="*.py" --include="*.js" . | grep -v "env" | grep -v "default"
```

---

## Environment Variable Documentation

### .env.example Structure

Every environment variable MUST be documented in `.env.example`:

```bash
# ============================================================
# CATEGORY NAME
# ============================================================

# VARIABLE_NAME - Description of what it does
# Values: Allowed values or range
# Required: Yes/No
# Default: Default value if not set (or "None" if required)
# Example: openssl rand -base64 32
VARIABLE_NAME=example_value

# Security tip or usage note if applicable
```

### Required Documentation Elements

For each environment variable, document:
1. **Purpose:** What it does
2. **Required:** Yes/No
3. **Default:** What happens if not set
4. **Example:** How to generate or typical value
5. **Security:** Any security implications

---

## Code Review Guidelines

When reviewing code that uses environment variables:

### ✅ Approve If:
- Secrets have no defaults (fail if missing)
- Error messages clearly state what env var is needed
- All env vars are in .env.example
- Ports/URLs have sensible defaults
- No passwords/keys visible in code

### ❌ Request Changes If:
- Hardcoded passwords (even in fallbacks)
- Hardcoded API keys
- Missing .env.example documentation
- Silent failures (missing env var with empty default)
- Unclear error messages

---

## Common Patterns

### Pattern 1: Required Secret
```python
def get_required_env(var_name, description):
    """Get required environment variable or fail with helpful message."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(
            f"{var_name} environment variable required.\n"
            f"Purpose: {description}\n"
            f"Set in .env file and restart services."
        )
    return value

# Usage
db_password = get_required_env('CONTEXT_DB_PASSWORD', 'Database password for PostgreSQL')
```

### Pattern 2: Optional with Default
```python
def get_env_int(var_name, default, description):
    """Get integer environment variable with default."""
    value = os.getenv(var_name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{var_name} must be an integer, got: {value}")

# Usage
port = get_env_int('POSTGRES_HOST_PORT', 5435, 'PostgreSQL host port')
```

### Pattern 3: Validated Environment Variable
```python
def get_env_url(var_name, default, description):
    """Get URL environment variable with validation."""
    url = os.getenv(var_name, default)
    if not url.startswith(('http://', 'https://')):
        raise ValueError(f"{var_name} must be a valid HTTP(S) URL")
    return url

# Usage
processor_url = get_env_url('PROCESSOR_URL', 'http://localhost:3200', 'Processor API URL')
```

---

## When You Discover Hardcoded Values

### Immediate Actions:

1. **Create Issue/Task**
   - Document the hardcoded value
   - Assess security impact
   - Plan fix strategy

2. **Assess Exposure**
   - Is it in git history? (If yes, consider secret compromised)
   - Is it in production? (If yes, rotate immediately)
   - Who has access? (Determine blast radius)

3. **Fix the Code**
   - Replace with environment variable
   - Update .env.example
   - Add validation/error handling
   - Test with missing/invalid values

4. **Rotate Secrets** (if exposed)
   - Generate new password/key
   - Update all deployments
   - Revoke old credential
   - Document incident

5. **Prevent Recurrence**
   - Add to pre-commit checks
   - Update security review checklist
   - Team education/documentation

---

## Examples from This Codebase

### ❌ Before (INSECURE):
```python
# hooks/agent_capture.py
DB_CONFIG = {
    'host': 'localhost',
    'port': 5435,  # Hardcoded
    'database': 'claude_memory',
    'user': 'memory_admin',
    'password': os.getenv('CONTEXT_DB_PASSWORD', 'RvnK7z05j...')  # HARDCODED FALLBACK!
}
```

### ✅ After (SECURE):
```python
# hooks/agent_capture.py
def get_db_config():
    """Get database configuration from environment variables."""
    password = os.getenv('CONTEXT_DB_PASSWORD')
    if not password:
        raise ValueError(
            "CONTEXT_DB_PASSWORD required. Set in .env file:\n"
            "  1. Generate: openssl rand -base64 32\n"
            "  2. Add to .env: CONTEXT_DB_PASSWORD=<generated>\n"
            "  3. Restart services: docker-compose restart"
        )

    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_HOST_PORT', '5435')),
        'database': os.getenv('POSTGRES_DB', 'claude_memory'),
        'user': os.getenv('POSTGRES_USER', 'memory_admin'),
        'password': password
    }

DB_CONFIG = get_db_config()
```

---

## Testing for Hardcoded Values

### Test Script

```bash
#!/bin/bash
# test-no-hardcoding.sh
# Verify no hardcoded secrets in codebase

echo "Testing for hardcoded values..."

# Remove .env temporarily to test
mv .env .env.test-backup 2>/dev/null

# Try to run scripts without .env
echo "Testing hooks/agent_capture.py without .env..."
python3 hooks/agent_capture.py 2>&1 | grep -q "CONTEXT_DB_PASSWORD required" && echo "✅ Properly fails" || echo "❌ Silent failure or hardcoded default used!"

# Restore .env
mv .env.test-backup .env 2>/dev/null

echo "Test complete"
```

---

## Summary: The Golden Rules

1. **NEVER** hardcode passwords, API keys, or secrets
2. **ALWAYS** fail loudly if required secrets are missing
3. **DOCUMENT** every environment variable in .env.example
4. **TEST** with missing environment variables before committing
5. **ROTATE** secrets immediately if exposed in code/git
6. **USE** environment variables for all environment-specific config
7. **VALIDATE** environment variable values at startup
8. **PROVIDE** helpful error messages when env vars are missing

---

**Remember:** Hardcoded values are technical debt that becomes security debt. Pay the small cost of proper configuration upfront to avoid the large cost of security incidents later.
