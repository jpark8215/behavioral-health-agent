-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    transcript TEXT NOT NULL,
    summary TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    key_points JSONB DEFAULT '[]'::jsonb,
    treatment_plan JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    audio_file_path TEXT,
    processing_status TEXT DEFAULT 'completed' CHECK (processing_status IN ('processing', 'completed', 'failed'))
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_content_hash ON sessions(content_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_processing_status ON sessions(processing_status);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_updated_at 
    BEFORE UPDATE ON sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your authentication needs)
-- For now, allow all operations (you should restrict this in production)
CREATE POLICY "Allow all operations on sessions" ON sessions
    FOR ALL USING (true);

-- Create audio_files table for storing audio metadata
CREATE TABLE IF NOT EXISTS audio_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    duration_seconds REAL,
    format TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processing_status TEXT DEFAULT 'uploaded' CHECK (processing_status IN ('uploaded', 'processing', 'transcribed', 'failed'))
);

-- Create indexes for audio_files
CREATE INDEX IF NOT EXISTS idx_audio_files_session_id ON audio_files(session_id);
CREATE INDEX IF NOT EXISTS idx_audio_files_created_at ON audio_files(created_at DESC);

-- Enable RLS for audio_files
ALTER TABLE audio_files ENABLE ROW LEVEL SECURITY;

-- Create policy for audio_files
CREATE POLICY "Allow all operations on audio_files" ON audio_files
    FOR ALL USING (true);