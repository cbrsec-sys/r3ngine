import React, { useEffect, useRef, useState } from 'react';
import type { LinkedInSessionStatus } from '../api/linkedin';
import {
  downloadLinkedInHelperScript,
  getLinkedInSessionStatus,
  revokeLinkedInSession,
  uploadLinkedInStateFile,
} from '../api/linkedin';

const StatusDot: React.FC<{ status: LinkedInSessionStatus | null }> = ({ status }) => {
  if (!status) return <span style={{ color: '#6b7280' }}>&#9899;</span>;
  if (status.is_valid) return <span style={{ color: '#22c55e' }}>&#9899;</span>;
  if (status.has_state_file || status.has_cookies) return <span style={{ color: '#f59e0b' }}>&#9899;</span>;
  return <span style={{ color: '#ef4444' }}>&#9899;</span>;
};

const statusLabel = (status: LinkedInSessionStatus | null): string => {
  if (!status) return 'Unknown';
  if (status.is_valid) {
    const when = status.last_validated_at
      ? new Date(status.last_validated_at).toLocaleString()
      : 'recently';
    return `Active — last validated ${when}`;
  }
  if (status.has_state_file || status.has_cookies) return 'Session present — not yet validated';
  return 'No session — authentication required';
};

const LinkedInSessionCard: React.FC = () => {
  const [status, setStatus] = useState<LinkedInSessionStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchStatus = async () => {
    try {
      setStatus(await getLinkedInSessionStatus());
    } catch {
      setError('Failed to fetch LinkedIn session status.');
    }
  };

  useEffect(() => { fetchStatus(); }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadLinkedInStateFile(file);
      await fetchStatus();
    } catch {
      setError('Upload failed. Ensure the file is a valid storage_state.json.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRevoke = async () => {
    setError(null);
    try {
      await revokeLinkedInSession();
      await fetchStatus();
    } catch {
      setError('Failed to revoke session.');
    }
  };

  const canRevoke = Boolean(status?.has_state_file || status?.has_cookies);

  return (
    <div className="card mb-3">
      <div className="card-header fw-semibold">LinkedIn Intelligence</div>
      <div className="card-body">
        <p className="mb-1">
          <strong>Status:</strong>{' '}
          <StatusDot status={status} /> {statusLabel(status)}
        </p>
        {status?.username && (
          <p className="mb-2 text-muted small">Account: {status.username}</p>
        )}
        {error && <div className="alert alert-danger py-2 small">{error}</div>}
        <div className="d-flex gap-2 flex-wrap mb-3">
          <button
            className="btn btn-primary btn-sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Uploading…' : 'Upload session state'}
          </button>
          <input
            type="file"
            accept=".json,application/json"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <button
            className="btn btn-outline-danger btn-sm"
            onClick={handleRevoke}
            disabled={!canRevoke}
          >
            Revoke session
          </button>
        </div>
        <p className="text-muted small mb-2">
          Run the helper script on your local machine, log in to LinkedIn in the browser
          that opens (including any MFA steps), then upload the exported{' '}
          <code>storage_state.json</code> here.
        </p>
        <button
          className="btn btn-outline-secondary btn-sm"
          onClick={downloadLinkedInHelperScript}
        >
          Download helper script
        </button>
      </div>
    </div>
  );
};

export default LinkedInSessionCard;
