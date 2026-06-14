function StatusBanner({ type = 'info', message }) {
  if (!message) return null;

  return <div className={`status-banner ${type}`}>{message}</div>;
}

export default StatusBanner;