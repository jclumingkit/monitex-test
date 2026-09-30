import AlarmDashboard from "./components/AlarmDashboard";
import { getProcessedEvents } from "./actions";

export default async function Home() {
  const events = await getProcessedEvents();

  return <AlarmDashboard initialEvents={events} />;
}
