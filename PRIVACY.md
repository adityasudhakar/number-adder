# Privacy Policy

**Last updated:** December 2024

## What We Collect

We collect the minimum data necessary to provide the Number Adder service:

| Data | Purpose | Retention |
|------|---------|-----------|
| Email address | Account identification | Until you delete your account |
| Password (hashed) | Authentication | Until you delete your account |
| Calculation history | Service functionality | Until you delete your account |

## What We Don't Collect

- IP addresses
- Browser information
- Location data
- Cookies (beyond authentication)
- Third-party tracking

## Your Rights (GDPR)

You have the right to:

### 1. Access Your Data
View all data we store about you.
```
GET /me
```

### 2. Export Your Data (Portability)
Download all your data in machine-readable JSON format.
```
GET /me/export
```

### 3. Delete Your Data (Right to Erasure)
Permanently delete your account and all associated data.
```
DELETE /me
```

When you delete your account:
- Your user record is immediately deleted
- All your calculation history is immediately deleted
- This action is irreversible

## Data Retention

- **Active accounts**: Data retained while account is active
- **Deleted accounts**: All data permanently deleted immediately upon account deletion
- **No backups**: We do not retain backups of deleted user data
- **No third-party sharing**: Your data is never sold or shared with third parties

## Data Security

- Passwords are hashed using bcrypt (never stored in plain text)
- All API endpoints require authentication
- Database uses foreign key constraints with CASCADE DELETE

## Lawful Basis

We process your data based on:
- **Contract**: To provide the service you signed up for
- **Consent**: By registering, you consent to this data processing

## Data Controller

[Your Name/Company]
[Your Email]

## Changes to This Policy

We will notify users of any material changes to this privacy policy.

## Contact

For privacy-related inquiries: [your-email@example.com]
