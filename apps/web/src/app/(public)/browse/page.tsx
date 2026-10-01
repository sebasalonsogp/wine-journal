import Link from "next/link";
export default function BrowsePage() {
  return (
    <main id="main" className="page-content">
      <h1>Browse wines</h1>
      <p className="page-intro">A little curiosity. Your next discovery.</p>
      <section className="empty-state">
        <h2>The wine library is taking shape.</h2>
        <p>
          Search, barcode scanning, and bottle recognition will live here. You’ll be able to look up
          a wine without an account.
        </p>
        <p className="availability-note">Wine lookup is coming in a later update.</p>
        <Link className="button" href="/capture" prefetch={false}>
          Add wine manually
        </Link>
      </section>
    </main>
  );
}
