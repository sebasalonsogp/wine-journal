import { notFound } from "next/navigation";
import { WineDetail } from "@/features/my-wines/wine-detail";

export default async function WinePage({ params }: { params: Promise<{ wineId: string }> }) {
  const { wineId } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(wineId)) notFound();
  return <WineDetail wineId={wineId} />;
}
