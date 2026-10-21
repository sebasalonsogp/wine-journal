import { notFound } from "next/navigation";
import { OccasionDetail } from "@/features/occasions/occasion-views";

export default async function OccasionPage({
  params,
}: {
  params: Promise<{ occasionId: string }>;
}) {
  const { occasionId } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(occasionId))
    notFound();
  return <OccasionDetail occasionId={occasionId} />;
}
