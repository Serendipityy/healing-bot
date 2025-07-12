# Clean up old files after refactoring

## Files to move to backup (not used anymore):

### Main old file:
- `app.py` (original monolithic file)

### Cache files:
- `__pycache__/` (can be regenerated)

### Backup existing files before refactor
- Move unused files to `backup/` folder
- Keep important files like:
  - `ragbase/` (still used)
  - `config/` (still used) 
  - `chat_storage.py` (still used)
  - `chat_history.db` (still used)
  - `.env` (still used)
  - `images/` (still used)

## Files still in use:
- `ragbase/` - RAG components
- `config/` - Configuration
- `chat_storage.py` - Database operations
- `chat_history.db` - SQLite database
- `.env` - Environment variables
- `images/` - UI images
- All evaluation and analysis files
