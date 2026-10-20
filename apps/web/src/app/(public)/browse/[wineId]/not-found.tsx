import Link from "next/link";

export default function WineNotFound() {
  return (
    <main id="main" className="page-content">
      <section className="empty-state">
        <h1>Wine not found</h1>
        <p>This release isn’t in our library. Try searching by wine or producer.</p>
        <Link className="button" href="/browse">
          Search wines
        </Link>
      </section>
    </main>
  );
}
