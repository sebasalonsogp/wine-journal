import { CaptureForm } from "@/features/capture/capture-form";
import { uuid } from "@/features/capture/draft";

export default async function CapturePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { wine } = await searchParams;
  return <CaptureForm wineId={typeof wine === "string" && uuid.test(wine) ? wine : undefined} />;
}
