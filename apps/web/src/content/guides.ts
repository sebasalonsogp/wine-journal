export type WineGuide = {
  slug: string;
  category: string;
  title: string;
  introduction: string;
  reviewedOn: string;
  sections: { title: string; text: string }[];
  reflection: string;
  searches: string[];
  source: { title: string; url: string };
};

// Original editorial copy. Source dates are reviewed explicitly, never generated at build time.
export const wineGuides: readonly WineGuide[] = [
  {
    slug: "first-tasting",
    category: "Tasting",
    title: "A first tasting, in your own words",
    introduction:
      "You do not need a perfect description. A few familiar words can help you remember a wine.",
    reviewedOn: "2026-10-23",
    sections: [
      {
        title: "Start with a familiar impression",
        text: "Notice the wine’s appearance, then its smell and taste. Does it remind you of a fruit, a flower or something from your kitchen? A broad impression is useful even when you cannot name a specific aroma.",
      },
      {
        title: "Separate flavor from feeling",
        text: "Acidity can make your mouth water; tannin can feel drying. Those sensations are different from the flavors you notice. Describe them separately if that helps you remember the experience.",
      },
      {
        title: "Leave room for your own opinion",
        text: "Record what stood out and whether you enjoyed it. A producer’s description is a reference, not an answer to copy. In your journal, notes belong to that drinking entry; your current wine rating can change independently.",
      },
    ],
    reflection:
      "Try one sentence: “It reminded me of ___, felt ___, and I enjoyed ___.” Leave any part blank.",
    searches: ["Cabernet Sauvignon", "Chardonnay"],
    source: {
      title: "WSET — Wine tasting information",
      url: "https://www.wsetglobal.com/knowledge-centre/blog/2019/november/how-to-build-your-wine-tasting-skills",
    },
  },
  {
    slug: "wine-styles",
    category: "Styles & grapes",
    title: "Find your way around wine styles",
    introduction:
      "Color, bubbles, body and sweetness describe different things. Start with one distinction at a time.",
    reviewedOn: "2026-10-23",
    sections: [
      {
        title: "Still, sparkling or fortified",
        text: "Still wines have no noticeable fizz. Sparkling wines contain bubbles. Fortified wines have spirit added during production. These broad types are a starting point, not a ranking of quality.",
      },
      {
        title: "A grape is a clue, not the whole story",
        text: "Chardonnay, Sauvignon Blanc and Riesling are white grape varieties; Cabernet Sauvignon and Pinot Noir are black grape varieties used for red wines. Winemaking also matters: Chardonnay, for example, can be made in different styles. Most rosé gets its pink color from shorter contact with black grape skins.",
      },
      {
        title: "Body and sweetness are separate",
        text: "Body describes how light or full a wine feels. Sweetness describes its sugar-related taste; dry means it does not taste sweet. Record these separately instead of using “strong” to mean both.",
      },
    ],
    reflection:
      "When revisiting a bottle, note its type and one sensation you remember. You can add more detail later.",
    searches: ["Chardonnay", "Cabernet Sauvignon", "Riesling"],
    source: {
      title: "WSET — A guide to wine types and styles",
      url: "https://www.wsetglobal.com/knowledge-centre/blog/2023/october/03/how-many-wine-types-and-styles-are-there",
    },
  },
  {
    slug: "food-pairings",
    category: "Food pairings",
    title: "Let the food be part of the story",
    introduction:
      "A useful pairing is one you enjoy. Treat suggestions as experiments, not rules you have to follow.",
    reviewedOn: "2026-10-23",
    sections: [
      {
        title: "Start with something you like",
        text: "A celebrated pairing is not a guarantee of enjoyment. Your preferences matter, so start with a wine and food you already enjoy rather than choosing only because a combination is considered classic.",
      },
      {
        title: "Think beyond red or white",
        text: "Salt, acidity, fat, sweetness and chilli in a dish can change how a wine tastes. Consider the sauce and seasoning as well as the main ingredient. Salty, fatty food can make a tannic wine seem softer; an acidic accompaniment can soften the impression of acidity in a wine.",
      },
      {
        title: "Remember the combination",
        text: "Write down the dish and what changed with it. “Softer with the cheese” is more useful to your future self than a pairing score. Another person may notice something different.",
      },
    ],
    reflection:
      "If you are already having wine with a meal, compare your first impression with how it tastes alongside the food.",
    searches: ["Cabernet Sauvignon", "Sauvignon Blanc"],
    source: {
      title: "WSET — Food and wine pairing principles",
      url: "https://www.wsetglobal.com/knowledge-centre/blog/2023/july/13/four-rules-to-masterful-food-and-wine-pairing",
    },
  },
  {
    slug: "regions-and-labels",
    category: "Regions & labels",
    title: "Read the place on the label",
    introduction:
      "A region tells you about origin. Read it alongside the producer, grape and vintage to understand the bottle.",
    reviewedOn: "2026-10-23",
    sections: [
      {
        title: "Separate place from producer",
        text: "The producer identifies who made the wine. A geographical indication identifies where its grapes were grown. In some regions, that designation also sets rules about grape varieties or production. A wine’s individual name may refer to a vineyard, a person or something else entirely.",
      },
      {
        title: "Use a region as context",
        text: "Climate influences grape ripeness and wine style. Some European labels emphasize the region instead of naming the grape, so a place name may need a little research. Origin helps set expectations; it does not tell you exactly what every bottle will taste like.",
      },
      {
        title: "Check the year separately",
        text: "A vintage refers to the grape harvest year. Keep it separate from the producer and wine name when recording a bottle. If you cannot identify the vintage, leave it unknown rather than guessing from another date on the label.",
      },
    ],
    reflection:
      "Pick a label and find its producer, origin and vintage. Follow the producer reference on its wine page when a detail is missing.",
    searches: ["Monte Bello", "Seven Oaks"],
    source: {
      title: "WSET — Common features on wine labels",
      url: "https://www.wsetglobal.com/knowledge-centre/blog/2019/how-to-read-wine-labels-part-one-common-features-on-wine-labels",
    },
  },
];
