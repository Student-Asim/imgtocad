import { useEffect, useState } from 'react';

function VisitorCount() {
  const [count, setCount] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadVisitorCount = async () => {
      try {
        const response = await fetch('http://localhost:8000/analytics/visit', {
          method: 'POST',
        });

        if (!response.ok) {
          throw new Error('Failed to load visitor count');
        }

        const data = await response.json();
        setCount(data.count);
      } catch (err) {
        setError(err.message || 'Something went wrong');
      }
    };

    loadVisitorCount();
  }, []);

  if (error) {
    return <p style={{ color: '#ff6b6b' }}>Visitor count unavailable</p>;
  }

  return (
    <p style={{ color: '#cbd5e1', marginTop: '12px' }}>
      {count !== null ? `Visitors: ${count}` : 'Loading visitors...'}
    </p>
  );
}

export default VisitorCount;