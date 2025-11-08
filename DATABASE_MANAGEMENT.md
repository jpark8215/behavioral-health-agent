# Database Management Guide

Complete guide for viewing and managing your PostgreSQL database.

## Quick Access Methods

### Method 1: Command Line (psql) ⚡ Fastest

#### Common Commands

**View recent sessions:**
```bash
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT id, created_at, summary FROM sessions ORDER BY created_at DESC LIMIT 10;"
```

**Count total sessions:**
```bash
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM sessions;"
```

**View specific session:**
```bash
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT * FROM sessions WHERE id = 'your-session-id-here';"
```

**View session with transcript:**
```bash
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT id, summary, LENGTH(transcript) as transcript_length FROM sessions WHERE id = 'your-session-id';"
```

**Delete a session:**
```bash
docker-compose exec postgres psql -U postgres -d postgres -c "DELETE FROM sessions WHERE id = 'your-session-id';"
```

**Delete all sessions (careful!):**
```bash
docker-compose exec postgres psql -U postgres -d postgres -c "TRUNCATE TABLE sessions;"
```

#### Interactive Shell

**Enter psql shell:**
```bash
docker-compose exec postgres psql -U postgres -d postgres
```

**Once inside, useful commands:**
```sql
-- List all tables
\dt

-- Describe sessions table structure
\d sessions

-- View recent sessions
SELECT id, created_at, summary 
FROM sessions 
ORDER BY created_at DESC 
LIMIT 5;

-- View sessions with diagnosis
SELECT id, created_at, diagnosis, summary 
FROM sessions 
WHERE diagnosis LIKE '%Anxiety%'
ORDER BY created_at DESC;

-- Count sessions by date
SELECT DATE(created_at) as date, COUNT(*) as count 
FROM sessions 
GROUP BY DATE(created_at) 
ORDER BY date DESC;

-- View full session details
SELECT * FROM sessions WHERE id = 'your-session-id';

-- Exit shell
\q
```

---

## Method 2: pgAdmin (Web GUI) 🖥️ Best for Management

### Setup pgAdmin

**1. Start pgAdmin:**
```bash
docker-compose --profile tools up -d pgadmin
```

**2. Access pgAdmin:**
- Open browser: http://localhost:5050
- Login:
  - Email: `admin@localhost.com`
  - Password: `admin`

**3. Connect to Database:**

Click "Add New Server" and enter:

**General Tab:**
- Name: `Behavioral Health DB`

**Connection Tab:**
- Host: `postgres`
- Port: `5432`
- Maintenance database: `postgres`
- Username: `postgres`
- Password: (your POSTGRES_PASSWORD from .env)

**4. Browse Data:**
- Expand: Servers → Behavioral Health DB → Databases → postgres → Schemas → public → Tables
- Right-click `sessions` → View/Edit Data → All Rows

### pgAdmin Features

- **Visual Query Builder**: Build queries without SQL
- **Data Export**: Export to CSV, JSON, etc.
- **Backup/Restore**: Full database backup and restore
- **Query Tool**: Run custom SQL queries
- **Table Designer**: Modify table structure
- **Performance Dashboard**: Monitor database performance

### Stop pgAdmin (when done):
```bash
docker-compose --profile tools down pgadmin
```

---

## Method 3: Database Client Tools 🔧

### DBeaver (Free, Cross-platform)

**1. Download:** https://dbeaver.io/download/

**2. Connect:**
- Host: `localhost`
- Port: `5432`
- Database: `postgres`
- Username: `postgres`
- Password: (your POSTGRES_PASSWORD)

### TablePlus (Mac/Windows)

**1. Download:** https://tableplus.com/

**2. Connect:**
- Type: PostgreSQL
- Host: `localhost`
- Port: `5432`
- User: `postgres`
- Password: (your POSTGRES_PASSWORD)
- Database: `postgres`

### DataGrip (JetBrains, Paid)

Professional database IDE with advanced features.

---

## Common Database Tasks

### View Sessions

**All sessions:**
```sql
SELECT id, created_at, summary, diagnosis 
FROM sessions 
ORDER BY created_at DESC;
```

**Sessions from today:**
```sql
SELECT id, created_at, summary 
FROM sessions 
WHERE DATE(created_at) = CURRENT_DATE
ORDER BY created_at DESC;
```

**Sessions with specific diagnosis:**
```sql
SELECT id, created_at, diagnosis, summary 
FROM sessions 
WHERE diagnosis LIKE '%Anxiety%'
ORDER BY created_at DESC;
```

### Search Sessions

**Search by transcript content:**
```sql
SELECT id, created_at, summary 
FROM sessions 
WHERE transcript ILIKE '%anxiety%'
ORDER BY created_at DESC;
```

**Search by summary:**
```sql
SELECT id, created_at, summary 
FROM sessions 
WHERE summary ILIKE '%stress%'
ORDER BY created_at DESC;
```

### Manage Sessions

**Update a session:**
```sql
UPDATE sessions 
SET summary = 'Updated summary text'
WHERE id = 'your-session-id';
```

**Delete old sessions:**
```sql
DELETE FROM sessions 
WHERE created_at < NOW() - INTERVAL '30 days';
```

**Delete duplicate sessions:**
```sql
DELETE FROM sessions a
USING sessions b
WHERE a.id > b.id 
AND a.content_hash = b.content_hash;
```

### Statistics

**Count sessions by diagnosis:**
```sql
SELECT diagnosis, COUNT(*) as count 
FROM sessions 
GROUP BY diagnosis 
ORDER BY count DESC;
```

**Average transcript length:**
```sql
SELECT AVG(LENGTH(transcript)) as avg_length 
FROM sessions;
```

**Sessions per day:**
```sql
SELECT DATE(created_at) as date, COUNT(*) as sessions 
FROM sessions 
GROUP BY DATE(created_at) 
ORDER BY date DESC;
```

---

## Database Backup & Restore

### Backup Database

**Full backup:**
```bash
docker-compose exec postgres pg_dump -U postgres postgres > backup_$(date +%Y%m%d).sql
```

**Backup specific table:**
```bash
docker-compose exec postgres pg_dump -U postgres -t sessions postgres > sessions_backup.sql
```

**Compressed backup:**
```bash
docker-compose exec postgres pg_dump -U postgres postgres | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore Database

**Restore from backup:**
```bash
docker-compose exec -T postgres psql -U postgres postgres < backup_20241108.sql
```

**Restore from compressed backup:**
```bash
gunzip -c backup_20241108.sql.gz | docker-compose exec -T postgres psql -U postgres postgres
```

---

## Database Maintenance

### Check Database Size

```bash
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT pg_size_pretty(pg_database_size('postgres'));"
```

### Check Table Size

```bash
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT pg_size_pretty(pg_total_relation_size('sessions'));"
```

### Vacuum Database (Optimize)

```bash
docker-compose exec postgres psql -U postgres -d postgres -c "VACUUM ANALYZE sessions;"
```

### View Active Connections

```bash
docker-compose exec postgres psql -U postgres -d postgres -c "SELECT * FROM pg_stat_activity WHERE datname = 'postgres';"
```

---

## Troubleshooting

### Can't Connect to Database

**Check if PostgreSQL is running:**
```bash
docker-compose ps postgres
```

**Check PostgreSQL logs:**
```bash
docker-compose logs postgres --tail 50
```

**Restart PostgreSQL:**
```bash
docker-compose restart postgres
```

### Database is Slow

**Check active queries:**
```sql
SELECT pid, now() - query_start as duration, query 
FROM pg_stat_activity 
WHERE state = 'active' 
ORDER BY duration DESC;
```

**Kill long-running query:**
```sql
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE pid = 12345;  -- Replace with actual PID
```

### Reset Database (Delete All Data)

**⚠️ WARNING: This deletes ALL sessions!**

```bash
docker-compose exec postgres psql -U postgres -d postgres -c "TRUNCATE TABLE sessions CASCADE;"
```

**Or completely reset:**
```bash
docker-compose down -v  # Deletes all volumes including database
docker-compose up -d    # Starts fresh
```

---

## Security Best Practices

### Change Default Password

**1. Update .env file:**
```bash
POSTGRES_PASSWORD=your-strong-password-here
```

**2. Restart services:**
```bash
docker-compose down
docker-compose up -d
```

### Restrict Access

**For production, don't expose port 5432:**

In `docker-compose.yml`, remove or comment out:
```yaml
# ports:
#   - "5432:5432"
```

### Regular Backups

**Set up automated backups (cron job):**
```bash
# Add to crontab (crontab -e)
0 2 * * * cd /path/to/project && docker-compose exec postgres pg_dump -U postgres postgres | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

---

## Quick Reference

| Task | Command |
|------|---------|
| View sessions | `docker-compose exec postgres psql -U postgres -d postgres -c "SELECT * FROM sessions LIMIT 10;"` |
| Count sessions | `docker-compose exec postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM sessions;"` |
| Delete session | `docker-compose exec postgres psql -U postgres -d postgres -c "DELETE FROM sessions WHERE id='xxx';"` |
| Backup database | `docker-compose exec postgres pg_dump -U postgres postgres > backup.sql` |
| Restore database | `docker-compose exec -T postgres psql -U postgres postgres < backup.sql` |
| Start pgAdmin | `docker-compose --profile tools up -d pgadmin` |
| Access pgAdmin | http://localhost:5050 |
| Interactive shell | `docker-compose exec postgres psql -U postgres -d postgres` |

---

## Additional Resources

- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **pgAdmin Documentation**: https://www.pgadmin.org/docs/
- **SQL Tutorial**: https://www.postgresqltutorial.com/

---

**Need Help?**

Check the main README.md or run:
```bash
docker-compose logs postgres
```
