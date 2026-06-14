import VisitorCount from '../components/VisitorCount';
import { Cpu, FileImage, Clock3, FolderOutput } from 'lucide-react';

const items = [
  {
    icon: <FileImage size={18} />,
    title: 'Panorama input',
    text: 'Upload a JPEG or PNG panorama and send it directly to the FastAPI pipeline.',
  },
  {
    icon: <Cpu size={18} />,
    title: 'Pipeline modes',
    text: 'Choose instant generation for a blocking workflow or async generation for long model runs.',
  },
  {
    icon: <Clock3 size={18} />,
    title: 'Async polling',
    text: 'Track job progress from the returned job id and show results when processing is complete.',
  },
  {
    icon: <FolderOutput size={18} />,
    title: 'Output review',
    text: 'Preview debug images and open download links for PNG and DXF outputs.',
  },
];

function Dashboard() {
  return (
    <div className="page">
      <section className="hero panel panel-hero">
        <p className="eyebrow">Floor plan generation workspace</p>
        <h2>React dashboard for your FastAPI floorplan pipeline.</h2>
        <VisitorCount />
        <p className="hero-copy">
          The interface is tuned for an AI-product feel without flashy gradients:
          dark graphite surfaces, restrained teal highlights, technical cards,
          and image-first output review.
        </p>
      </section>

      <section className="stats-grid">
        <article className="stat-card">
          <span>Accepted types</span>
          <strong>JPG, JPEG, PNG</strong>
        </article>

        <article className="stat-card">
          <span>Sync route</span>
          <strong>POST /generate</strong>
        </article>

        <article className="stat-card">
          <span>Async route</span>
          <strong>POST /generate/async</strong>
        </article>

        <article className="stat-card">
          <span>Status route</span>
          <strong>GET /jobs/:id</strong>
        </article>
      </section>

      <section className="feature-grid">
        {items.map((item) => (
          <article className="feature-card" key={item.title}>
            <div className="feature-icon">{item.icon}</div>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

export default Dashboard;