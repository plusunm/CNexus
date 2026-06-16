import { redirect } from "next/navigation";

export default function CognitiveRedirect() {
  redirect("/shell?layout=cognitive");
}
