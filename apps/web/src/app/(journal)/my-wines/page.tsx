export default function MyWinesPage() {
  return (
    <main id="main" className="page-content">
      <h1>My wines</h1>
      <p className="page-intro">Wines you’ve tried. Moments worth keeping.</p>
      <section className="empty-state">
        <h2>Your first page is waiting.</h2>
        <p>This is where your wines, personal notes, and memories will come together.</p>
        <p className="availability-note">Wine logging is coming next. Your account is ready.</p>
      </section>
      <footer className="journal-footer">
        Your journal is private.<span>Every vintage keeps its own story.</span>
      </footer>
    </main>
  );
}
