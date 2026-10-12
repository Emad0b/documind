CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE, password TEXT);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, owner TEXT REFERENCES users(id) ON DELETE CASCADE, expires REAL);
CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, owner TEXT REFERENCES users(id), name TEXT, pages INTEGER, digest TEXT, status TEXT, error TEXT, created REAL, UNIQUE(owner,digest));
CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, doc TEXT REFERENCES documents(id) ON DELETE CASCADE, page INTEGER, position INTEGER, text TEXT, embedding TEXT, model TEXT);
CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc);
CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, owner TEXT REFERENCES users(id), title TEXT, created REAL);
CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, conversation TEXT REFERENCES conversations(id) ON DELETE CASCADE, role TEXT, payload TEXT, created REAL);
CREATE TABLE IF NOT EXISTS usage (id TEXT PRIMARY KEY, owner TEXT REFERENCES users(id), latency REAL, input_tokens INTEGER, output_tokens INTEGER, cost REAL, created REAL);
