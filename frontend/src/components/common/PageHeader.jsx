export default function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="section-header">
      <div>
        <p className="section-eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p className="section-copy">{description}</p>
      </div>
      {action || null}
    </div>
  );
}
