import { useEffect, useRef, useState } from 'react';
import FileUpload from '../components/FileUpload';
import ResultCard from '../components/ResultCard';
import StatusBanner from '../components/StatusBanner';
import { generateAsync, getJob } from '../api/floorplan';

function GenerateAsync() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState('');
  const [status, setStatus] = useState('idle');
  const [detail, setDetail] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const startPolling = (id) => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    timerRef.current = setInterval(async () => {
      try {
        const data = await getJob(id);

        if (data.status === 'processing') {
          setStatus('processing');
          setDetail(data.detail || 'Job still processing');
          return;
        }

        setStatus('done');
        setDetail('Job complete');
        setResult(data);
        clearInterval(timerRef.current);
      } catch (err) {
        setStatus('error');
        setError(err.message);
        clearInterval(timerRef.current);
      }
    }, 2500);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setPreviewLoading(true);
    setResult(null);
    setError('');
    setDetail('');
    setJobId('');
    setStatus('idle');

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl('');
    }

    try {
      const data = await generateAsync(file);
      setJobId(data.job_id);
      setStatus(data.status || 'processing');
      setDetail('Background generation started');
      startPolling(data.job_id);

      const previewForm = new FormData();
      previewForm.append('file', file);

      const previewRes = await fetch('http://localhost:8000/generate-preview', {
        method: 'POST',
        body: previewForm,
      });

      if (!previewRes.ok) {
        throw new Error('Failed to generate preview image');
      }

      const blob = await previewRes.blob();
      const objectUrl = URL.createObjectURL(blob);
      setPreviewUrl(objectUrl);
    } catch (err) {
      setError(err.message);
      setStatus('error');
    } finally {
      setLoading(false);
      setPreviewLoading(false);
    }
  };

  return (
    <div className="page">
      <section className="panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Async generation</p>
            <h2>Start long processing and poll the job state.</h2>
          </div>
        </div>

        <p className="section-copy">
          Use this for heavier model runs. The UI stores the returned job id
          and keeps checking until outputs are ready.
        </p>

        <FileUpload
          file={file}
          onChange={setFile}
          onSubmit={handleSubmit}
          isLoading={loading}
          buttonLabel="Start async job"
        />
      </section>

      <section className="panel job-panel">
        <div className="job-grid">
          <div className="job-box">
            <span>Job ID</span>
            <strong>{jobId || 'Not started yet'}</strong>
          </div>

          <div className="job-box">
            <span>Status</span>
            <strong className={`status-text ${status}`}>{status}</strong>
          </div>

          <div className="job-box">
            <span>Message</span>
            <strong>{detail || 'Waiting for submission'}</strong>
          </div>
        </div>
      </section>

      <StatusBanner type="error" message={error} />

      {status === 'processing' && !error ? (
        <StatusBanner
          type="info"
          message="Job is processing. Polling every 2.5 seconds."
        />
      ) : null}

      {previewLoading ? (
        <StatusBanner type="info" message="Generating preview image..." />
      ) : null}

      <ResultCard result={result} />

      {previewUrl ? (
        <section className="panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Final preview</p>
              <h2>Generated CAD image</h2>
            </div>
          </div>

          <img
            src={previewUrl}
            alt="Generated floor plan preview"
            style={{
              width: '100%',
              maxWidth: '900px',
              borderRadius: '16px',
              display: 'block',
              marginTop: '16px',
            }}
          />
        </section>
      ) : null}
    </div>
  );
}

export default GenerateAsync;