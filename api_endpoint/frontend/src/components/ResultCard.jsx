import { Download, FileImage } from 'lucide-react';
import { resolveApiUrl } from '../api/floorplan';

function LinkButton({ href, label, icon }) {
  if (!href) return null;

  return (
    <a
      className="link-btn"
      href={resolveApiUrl(href)}
      target="_blank"
      rel="noreferrer"
    >
      {icon}
      <span>{label}</span>
    </a>
  );
}

function ResultCard({ result }) {
  if (!result) return null;

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Result</p>
          <h2>Generated floor plan</h2>
        </div>
      </div>

      <div className="action-grid">
        <LinkButton
          href={result.download_png}
          label="Download PNG"
          icon={<FileImage size={16} />}
        />

        <LinkButton
          href={result.download_dxf}
          label="Download DXF"
          icon={<Download size={16} />}
        />
      </div>

      {result.download_png ? (
        <div className="result-preview" style={{ marginTop: '20px' }}>
          <img
            src={resolveApiUrl(result.download_png)}
            alt="Generated CAD floor plan"
            className="debug-image"
            loading="lazy"
            style={{
              width: '100%',
              maxWidth: '900px',
              borderRadius: '16px',
              display: 'block',
            }}
          />
        </div>
      ) : null}
    </section>
  );
}

export default ResultCard;