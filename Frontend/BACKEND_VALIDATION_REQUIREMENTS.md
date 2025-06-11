# Backend Validation Requirements

## Username Validation

To prevent confusion in the authentication system, the backend should enforce that usernames cannot be email addresses.

### Required Backend Changes:

#### 1. Update User Registration Validation

```python
import re

def validate_username(username: str) -> bool:
    """
    Validate that username is not an email format
    """
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    
    # Username must be at least 2 characters
    if len(username) < 2:
        return False
    
    # Username cannot be an email format
    if re.match(email_regex, username):
        return False
        
    return True
```

#### 2. Update Pydantic Models

```python
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    
    @validator('username')
    def username_cannot_be_email(cls, v):
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if re.match(email_regex, v):
            raise ValueError('Username cannot be an email address')
        if len(v) < 2:
            raise ValueError('Username must be at least 2 characters')
        return v
```

#### 3. Database Constraints (Optional)

Consider adding a database constraint to enforce this at the DB level:

```sql
-- PostgreSQL example
ALTER TABLE users ADD CONSTRAINT username_not_email 
CHECK (username !~ '^[^\s@]+@[^\s@]+\.[^\s@]+$');
```

#### 4. Error Messages

Update error messages to be consistent with frontend:

```python
"Username must be at least 2 characters and cannot be an email address"
```

### Why This Validation Is Important:

1. **Prevents Login Confusion**: Ensures the frontend email detection logic works reliably
2. **Clearer User Intent**: Forces users to choose distinct usernames vs emails
3. **Prevents Conflicts**: Avoids situations where username@domain.com exists as both username and email
4. **Better Security**: Reduces potential attack vectors related to authentication confusion

### Testing:

Test these scenarios should fail:
- `user@example.com` as username ❌
- `test@domain.co.uk` as username ❌
- `simple@email.org` as username ❌

These should pass:
- `username123` ✅
- `user_name` ✅
- `testuser` ✅ 