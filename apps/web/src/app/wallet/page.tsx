import { AppScreenShell } from "@/components/app/app-screen-shell";
import { WalletWorkspace } from "@/components/app/wallet-workspace";

export const metadata = {
  title: "Wallet — Satta",
  description: "Deposit, withdraw, and view your transaction history.",
};

export default function WalletPage() {
  return (
    <AppScreenShell eyebrow="Wallet" title="Deposits & Withdrawals">
      <WalletWorkspace />
    </AppScreenShell>
  );
}
