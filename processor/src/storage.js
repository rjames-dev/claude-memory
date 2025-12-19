/**
 * PostgreSQL Storage
 * Stores context snapshots in the database
 */

const { Pool } = require('pg');

// Create PostgreSQL connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000
});

pool.on('error', (err) => {
  console.error('Unexpected error on idle client', err);
});

/**
 * Store context snapshot in database with upsert logic
 *
 * Upsert Strategy:
 * - If session_id OR transcript_path already exists, update existing record
 * - Otherwise, insert new record
 * - Prevents duplicate captures from PreCompact + SessionStart hooks
 */
async function storeSnapshot(snapshot) {
  const client = await pool.connect();

  try {
    // First, check if this session/transcript already exists
    let existingId = null;
    if (snapshot.session_id || snapshot.transcript_path) {
      const checkQuery = `
        SELECT id FROM context_snapshots
        WHERE session_id = $1 OR transcript_path = $2
        LIMIT 1
      `;
      const checkResult = await client.query(checkQuery, [
        snapshot.session_id || null,
        snapshot.transcript_path || null
      ]);

      if (checkResult.rows.length > 0) {
        existingId = checkResult.rows[0].id;
        console.log(`📝 Found existing snapshot ID ${existingId}, updating...`);
      }
    }

    if (existingId) {
      // UPDATE existing record
      const updateQuery = `
        UPDATE context_snapshots SET
          project_path = $1,
          session_id = $2,
          transcript_path = $3,
          raw_context = $4,
          summary = $5,
          embedding = $6,
          tags = $7,
          mentioned_files = $8,
          key_decisions = $9,
          bugs_fixed = $10,
          git_commit_hash = $11,
          git_branch = $12,
          trigger_event = $13,
          context_window_size = $14,
          storage_size_bytes = $15,
          timestamp = NOW()
        WHERE id = $16
        RETURNING id, timestamp
      `;

      const updateValues = [
        snapshot.project_path,
        snapshot.session_id || null,
        snapshot.transcript_path || null,
        snapshot.raw_context,
        snapshot.summary,
        `[${snapshot.embedding.join(',')}]`,
        snapshot.tags,
        snapshot.mentioned_files,
        snapshot.key_decisions,
        snapshot.bugs_fixed,
        snapshot.git_commit_hash,
        snapshot.git_branch,
        snapshot.trigger_event,
        snapshot.context_window_size,
        snapshot.storage_size_bytes,
        existingId
      ];

      const result = await client.query(updateQuery, updateValues);

      // Verify the update was successful
      const verifyQuery = 'SELECT id FROM context_snapshots WHERE id = $1';
      const verifyResult = await client.query(verifyQuery, [result.rows[0].id]);

      if (!verifyResult.rows.length) {
        throw new Error('Snapshot verification failed: Record not found after update');
      }

      return {
        id: result.rows[0].id,
        timestamp: result.rows[0].timestamp,
        upsert: 'updated'
      };

    } else {
      // INSERT new record
      const insertQuery = `
        INSERT INTO context_snapshots (
          project_path,
          session_id,
          transcript_path,
          raw_context,
          summary,
          embedding,
          tags,
          mentioned_files,
          key_decisions,
          bugs_fixed,
          git_commit_hash,
          git_branch,
          trigger_event,
          context_window_size,
          storage_size_bytes
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        RETURNING id, timestamp
      `;

      const insertValues = [
        snapshot.project_path,
        snapshot.session_id || null,
        snapshot.transcript_path || null,
        snapshot.raw_context,
        snapshot.summary,
        `[${snapshot.embedding.join(',')}]`,
        snapshot.tags,
        snapshot.mentioned_files,
        snapshot.key_decisions,
        snapshot.bugs_fixed,
        snapshot.git_commit_hash,
        snapshot.git_branch,
        snapshot.trigger_event,
        snapshot.context_window_size,
        snapshot.storage_size_bytes
      ];

      const result = await client.query(insertQuery, insertValues);

      // Verify the insert was successful
      const verifyQuery = 'SELECT id FROM context_snapshots WHERE id = $1';
      const verifyResult = await client.query(verifyQuery, [result.rows[0].id]);

      if (!verifyResult.rows.length) {
        throw new Error('Snapshot verification failed: Record not found after insert');
      }

      return {
        id: result.rows[0].id,
        timestamp: result.rows[0].timestamp,
        upsert: 'inserted'
      };
    }

  } catch (error) {
    console.error('Database storage error:', error);
    throw error;
  } finally {
    client.release();
  }
}

/**
 * Query snapshots by project path
 */
async function querySnapshots(project_path, limit = 10) {
  const client = await pool.connect();

  try {
    const query = `
      SELECT
        id,
        project_path,
        timestamp,
        summary,
        tags,
        mentioned_files,
        trigger_event,
        context_window_size
      FROM context_snapshots
      WHERE project_path = $1
      ORDER BY timestamp DESC
      LIMIT $2
    `;

    const result = await client.query(query, [project_path, limit]);
    return result.rows;

  } finally {
    client.release();
  }
}

/**
 * Test database connection
 */
async function testConnection() {
  const client = await pool.connect();

  try {
    const result = await client.query('SELECT NOW()');
    console.log('✅ Database connection successful:', result.rows[0].now);
    return true;
  } catch (error) {
    console.error('❌ Database connection failed:', error.message);
    return false;
  } finally {
    client.release();
  }
}

/**
 * Close pool (for graceful shutdown)
 */
async function closePool() {
  await pool.end();
  console.log('Database connection pool closed');
}

module.exports = {
  storeSnapshot,
  querySnapshots,
  testConnection,
  closePool
};
