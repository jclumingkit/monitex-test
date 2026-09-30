import { getProcessedEvents } from "../actions";
import DashboardContent from "../components/DashboardContent";

export default async function Page() {
  const events = await getProcessedEvents();

  return <DashboardContent initialEvents={events} />;
}
