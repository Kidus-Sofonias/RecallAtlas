import { Link } from 'react-router-dom';

export default function Terms() {
  return (
    <section className="page-content auth-page">
      <nav aria-label="Breadcrumb" className="breadcrumbs">
        <Link to="/">Home</Link><span>/</span><span>Terms of Service</span>
      </nav>
      <div className="page-heading">
        <p className="eyebrow">Recall Atlas</p>
        <h1>Terms of Service</h1>
      </div>
      <article className="card-surface terms-content">
        <p>
          By using Recall Atlas you agree to these terms. The platform provides an
          academic question archive. You must not upload answer keys, copyrighted
          material you cannot share, or unlawful content. User accounts are personal;
          do not share credentials. Content you upload remains yours; you grant Recall
          Atlas a license to store and display it per your visibility settings. We may
          remove content that violates policy. The service is provided as-is. See the
          privacy policy for data handling.
        </p>
        <Link className="button button-primary" to="/register">Create an account</Link>
      </article>
    </section>
  );
}
