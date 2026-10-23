import styles from "./tasting-help.module.css";

/** Writing guidance only: no access to drafts, catalog descriptions or ratings. */
export function TastingHelp() {
  return (
    <details className={styles.help}>
      <summary>Help me describe it</summary>
      <div className={styles.content}>
        <p>Pick a question if it helps. Write in your own words, or leave your notes for later.</p>
        <dl className={styles.prompts}>
          <dt>What did it remind you of?</dt>
          <dd>A familiar fruit, flower, spice or memory? Broad impressions are enough.</dd>
          <dt>How did it feel?</dt>
          <dd>Light or full? Mouth-watering or drying? Notice whatever stands out to you.</dd>
          <dt>What would you remember?</dt>
          <dd>Something you enjoyed, a food pairing, or the company you shared it with.</dd>
        </dl>
        <details className={styles.terms}>
          <summary>Body, acidity and tannin</summary>
          <dl>
            <dt>Body</dt>
            <dd>The sense of weight or fullness in your mouth.</dd>
            <dt>Acidity</dt>
            <dd>Notice how much the wine makes your mouth water.</dd>
            <dt>Tannin</dt>
            <dd>A drying or gripping sensation on your gums and tongue.</dd>
          </dl>
        </details>
        <p className={styles.footnote}>
          These are starting points, not tasting notes for this bottle. Only what you write goes
          into your entry.
        </p>
      </div>
    </details>
  );
}
