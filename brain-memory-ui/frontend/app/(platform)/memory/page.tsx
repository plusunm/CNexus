import { redirect } from "next/navigation";

export default function MemoryRedirect() {
  redirect("/shell?panel=memory&layout=float");
}
