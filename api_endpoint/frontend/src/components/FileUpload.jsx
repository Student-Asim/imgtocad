import { useMemo } from 'react';
import { Upload, Image as ImageIcon } from 'lucide-react';

function FileUpload({ file, onChange, onSubmit, isLoading, buttonLabel }) {
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : ''), [file]);

  return (
    <form className="upload-card" onSubmit={onSubmit}>
      <label className="dropzone">
        <input
          type="file"
          accept="image/png,image/jpeg,image/jpg"
          onChange={(e) => onChange(e.target.files?.[0] || null)}
          hidden
        />

        <div className="dropzone-icon">
          <Upload size={20} />
        </div>

        <div>
          <h3>Upload panorama</h3>
          <p>Accepts JPG or PNG panorama images for floor plan generation.</p>
        </div>
      </label>

      <div className="preview-box">
        {previewUrl ? (
          <img
            src={previewUrl}
            alt="Selected panorama preview"
            className="preview-image"
          />
        ) : (
          <div className="preview-empty">
            <ImageIcon size={22} />
            <span>No image selected</span>
          </div>
        )}
      </div>

      <div className="file-meta">
        <span>{file ? file.name : 'Choose a panorama to begin'}</span>

        <button
          type="submit"
          className="primary-btn"
          disabled={!file || isLoading}
        >
          {isLoading ? 'Processing...' : buttonLabel}
        </button>
      </div>
    </form>
  );
}

export default FileUpload;