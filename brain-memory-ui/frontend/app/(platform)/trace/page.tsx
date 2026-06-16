import { redirect } from "next/navigation";

export default function TraceRedirect() {
  redirect("/shell?layout=overview");
}
