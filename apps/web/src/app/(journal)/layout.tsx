import { JournalShell } from "@/features/auth/journal-shell";

export const dynamic = "force-dynamic";

export default function JournalLayout({ children }: { children: React.ReactNode }) {
  return <JournalShell>{children}</JournalShell>;
}
