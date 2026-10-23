import { notFound } from "next/navigation";
import { wineGuides } from "@/content/guides";
import { GuideArticle } from "@/features/guides/guide-views";

export function generateStaticParams() {
  return wineGuides.map(({ slug }) => ({ slug }));
}

type Props = { params: Promise<{ slug: string }> };

async function resolveGuide({ params }: Props) {
  const { slug } = await params;
  const guide = wineGuides.find((item) => item.slug === slug);
  if (!guide) notFound();
  return guide;
}

export async function generateMetadata(props: Props) {
  const guide = await resolveGuide(props);
  return { title: `${guide.title} | Wine Journal`, description: guide.introduction };
}

export default async function GuidePage(props: Props) {
  return <GuideArticle guide={await resolveGuide(props)} />;
}
