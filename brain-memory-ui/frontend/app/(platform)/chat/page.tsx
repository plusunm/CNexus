import { redirect } from "next/navigation";

export default function ChatRedirect() {
  redirect("/shell?panel=chat&layout=float");
}
