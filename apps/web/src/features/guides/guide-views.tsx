import Link from "next/link";
import { wineGuides, type WineGuide } from "@/content/guides";
import { browseHref } from "@/features/catalog/navigation";
import styles from "./guides.module.css";

export function GuidesIndex() {
  return (
    <main id="main" className={`page-content ${styles.index}`}>
      <p className={styles.eyebrow}>A little knowledge, a richer memory</p>
      <h1>Wine guides</h1>
      <p className="page-intro">
        Start with what’s in your glass. Four short guides to help you find your own words.
      </p>
      <ul className={styles.list} aria-label="Beginner wine guides">
        {wineGuides.map((guide, index) => (
          <li key={guide.slug}>
            <Link className={styles.guideLink} href={`/guides/${guide.slug}`}>
              <span className={styles.number} aria-hidden="true">
                0{index + 1}
              </span>
              <div>
                <p className={styles.eyebrow}>{guide.category}</p>
                <h2>{guide.title}</h2>
                <p className={styles.description}>{guide.introduction}</p>
              </div>
              <span aria-hidden="true" className={styles.arrow}>
                →
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <p className={styles.note}>Read in any order. Your own impressions belong in your journal.</p>
    </main>
  );
}

export function GuideArticle({ guide }: { guide: WineGuide }) {
  return (
    <main id="main" className={`page-content ${styles.articlePage}`}>
      <Link className="text-link" href="/guides">
        All wine guides
      </Link>
      <article className={styles.article}>
        <header>
          <p className={styles.eyebrow}>{guide.category}</p>
          <h1>{guide.title}</h1>
          <p className="page-intro">{guide.introduction}</p>
        </header>
        {guide.sections.map((section) => (
          <section key={section.title} className={styles.section}>
            <h2>{section.title}</h2>
            <p>{section.text}</p>
          </section>
        ))}
        <aside className={styles.reflection} aria-label="A prompt for your journal">
          <h2>A prompt for your journal</h2>
          <p>{guide.reflection}</p>
        </aside>
        <section className={styles.section} aria-labelledby="explore-wines-title">
          <h2 id="explore-wines-title">Explore the wine library</h2>
          <p>These searches are starting points. Our small library may not have a match yet.</p>
          <nav aria-label="Explore wines from this guide">
            <ul className={styles.searches}>
              {guide.searches.map((query) => (
                <li key={query}>
                  <Link className="text-link" href={browseHref(query)}>
                    Find {query}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </section>
        <section className={styles.sources} aria-labelledby="guide-sources-title">
          <h2 id="guide-sources-title">Sources and review</h2>
          <p>
            Original Wine Journal guide. Reviewed{" "}
            <time dateTime={guide.reviewedOn}>
              {new Date(`${guide.reviewedOn}T00:00:00Z`).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
                timeZone: "UTC",
              })}
            </time>
            .
          </p>
          <a
            className="text-link"
            href={guide.source.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {guide.source.title} (opens in a new tab)
          </a>
        </section>
      </article>
    </main>
  );
}

export function GuideNotFound() {
  return (
    <main id="main" className="page-content">
      <h1>Guide not found</h1>
      <p className="page-intro">That guide isn’t in the collection. Find a starting point below.</p>
      <Link className="text-link" href="/guides">
        All wine guides
      </Link>
    </main>
  );
}
