import { AccountDetails } from "@/features/auth/account-details";
export default function ProfilePage() {
  return (
    <main id="main" className="page-content">
      <h1>My account</h1>
      <AccountDetails />
    </main>
  );
}
